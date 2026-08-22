from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import ConflictError, NotFoundError
from .host import HostAdapter
from .models import ActionState, ExecutionMode, HostContext, PendingAction
from .policy import PolicyEngine
from .store import Store


@dataclass(frozen=True)
class ActionExecution:
    action: PendingAction
    error: str | None = None


class ActionService:
    def __init__(
        self,
        store: Store,
        policy: PolicyEngine,
        host_adapter: HostAdapter,
    ):
        self.store = store
        self.policy = policy
        self.host_adapter = host_adapter

    def propose(
        self,
        host: HostContext,
        *,
        conversation_id: str,
        run_id: str,
        action_type: str,
        payload: dict[str, Any],
        execution_mode: ExecutionMode,
        plugin_id: str | None,
    ) -> ActionExecution:
        decision = self.policy.decide(
            host=host,
            action_type=action_type,
            payload=payload,
            mode=execution_mode,
        )
        state = decision.state
        if plugin_id and not self.store.get_plugin(plugin_id).enabled:
            state = ActionState.BLOCKED_PLUGIN_DISABLED

        action = self.store.create_action(
            conversation_id=conversation_id,
            run_id=run_id,
            action_type=action_type,
            payload=payload,
            execution_mode=execution_mode,
            state=state,
            policy_decision=decision.evidence,
            plugin_id=plugin_id,
        )
        self._emit(action, "action.proposed")
        self._emit(action, "action.policy_evaluated")
        return self.execute(host, action) if state is ActionState.AUTO_APPLYING else ActionExecution(action)

    def edit(self, host: HostContext, action_id: str, payload: dict[str, Any]) -> PendingAction:
        action = self.store.get_action(host, action_id)
        if action.state not in {ActionState.AWAITING_CONFIRMATION, ActionState.EDITING}:
            raise ConflictError("Action is not editable")
        updated = self.store.update_action(
            action_id,
            state=ActionState.AWAITING_CONFIRMATION,
            payload=payload,
        )
        self._emit(updated, "action.updated")
        return updated

    def confirm(self, host: HostContext, action_id: str) -> ActionExecution:
        action = self.store.get_action(host, action_id)
        if action.state is not ActionState.AWAITING_CONFIRMATION:
            raise ConflictError("Action is not awaiting confirmation")
        decision = self.policy.decide(
            host=host,
            action_type=action.action_type,
            payload=action.payload,
            mode=ExecutionMode.CONFIRM_EACH,
        )
        if decision.state is ActionState.BLOCKED:
            blocked = self.store.update_action(
                action.id,
                state=ActionState.BLOCKED,
                policy_decision=decision.evidence,
            )
            self._emit(blocked, "action.updated")
            return ActionExecution(blocked, "Policy blocked the Action")
        return self.execute(host, action)

    def execute(self, host: HostContext, action: PendingAction) -> ActionExecution:
        if action.plugin_id and not self.store.get_plugin(action.plugin_id).enabled:
            blocked = self.store.update_action(action.id, state=ActionState.BLOCKED_PLUGIN_DISABLED)
            self._emit(blocked, "action.updated")
            return ActionExecution(blocked, "Plugin is disabled")

        applying_state = (
            ActionState.AUTO_APPLYING if action.state is ActionState.AUTO_APPLYING else ActionState.APPLYING
        )
        applying = self.store.update_action(action.id, state=applying_state)
        event_type = "action.auto_applying" if applying_state is ActionState.AUTO_APPLYING else "action.updated"
        self._emit(applying, event_type)
        try:
            executable = self._host_action(applying)
            result = self.host_adapter.apply_action(host, executable)
        except (ConflictError, NotFoundError) as error:
            failed = self.store.update_action(
                action.id,
                state=ActionState.FAILED,
                result={"error": str(error)},
            )
            self._emit(failed, "action.failed")
            return ActionExecution(failed, str(error))

        applied = self.store.update_action(action.id, state=ActionState.APPLIED, result=result)
        self._emit(applied, "action.applied")
        return ActionExecution(applied)

    def cancel(self, host: HostContext, action_id: str) -> PendingAction:
        action = self.store.get_action(host, action_id)
        if action.state not in {
            ActionState.AWAITING_CONFIRMATION,
            ActionState.EDITING,
            ActionState.BLOCKED_PLUGIN_DISABLED,
        }:
            raise ConflictError("Action cannot be cancelled")
        cancelled = self.store.update_action(action.id, state=ActionState.CANCELLED)
        self._emit(cancelled, "action.updated")
        return cancelled

    def undo(self, host: HostContext, action_id: str) -> ActionExecution:
        action = self.store.get_action(host, action_id)
        if action.state is not ActionState.APPLIED:
            raise ConflictError("Only applied Actions can be undone")
        undoing = self.store.update_action(action.id, state=ActionState.UNDOING)
        self._emit(undoing, "action.updated")
        try:
            result = self.host_adapter.undo_action(host, undoing)
        except (ConflictError, NotFoundError) as error:
            failed = self.store.update_action(
                action.id,
                state=ActionState.UNDO_FAILED,
                result={"error": str(error)},
            )
            self._emit(failed, "action.failed")
            return ActionExecution(failed, str(error))
        undone = self.store.update_action(action.id, state=ActionState.UNDONE, result=result)
        self._emit(undone, "action.updated")
        return ActionExecution(undone)

    def revalidate_plugin(self, host: HostContext, plugin_id: str) -> list[PendingAction]:
        if not self.store.get_plugin(plugin_id).enabled:
            raise ConflictError("Plugin is disabled")
        actions = self.store.list_plugin_actions(
            host,
            plugin_id,
            ActionState.BLOCKED_PLUGIN_DISABLED,
        )
        updated: list[PendingAction] = []
        for action in actions:
            decision = self.policy.decide(
                host=host,
                action_type=action.action_type,
                payload=action.payload,
                mode=action.execution_mode,
            )
            current = self.store.update_action(
                action.id,
                state=decision.state,
                policy_decision=decision.evidence,
            )
            self._emit(current, "action.policy_evaluated")
            updated.append(current)
        return updated

    @staticmethod
    def _host_action(action: PendingAction) -> PendingAction:
        if action.action_type == "sample.records.create":
            return action.model_copy(update={"action_type": "host_data.record.create"})
        return action

    def _emit(self, action: PendingAction, event_type: str) -> None:
        if not action.run_id:
            return
        self.store.append_event(
            scope_kind="run",
            scope_id=action.run_id,
            event_type=event_type,
            payload={"action": action.model_dump(mode="json")},
            conversation_id=action.conversation_id,
            run_id=action.run_id,
        )
