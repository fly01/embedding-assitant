<script setup lang="ts">
import { reactive, watch } from "vue";
import type { PendingAction } from "../types";

const props = defineProps<{ action: PendingAction }>();
const emit = defineEmits<{
  confirm: [id: string];
  cancel: [id: string];
  undo: [id: string];
  edit: [id: string, payload: Record<string, unknown>];
  openAttachment: [id: string];
}>();
const draft = reactive<Record<string, any>>({ ...props.action.payload });

watch(
  () => props.action.payload,
  (payload) => Object.assign(draft, payload),
);

function save(): void {
  emit("edit", props.action.id, { ...draft });
}
</script>

<template>
  <article class="action-card" :data-state="action.state">
    <header>
      <div>
        <small>{{ action.action_type }}</small>
        <h4>{{ action.state.replaceAll("_", " ") }}</h4>
      </div>
      <span class="action-mode">{{ action.execution_mode }}</span>
    </header>

    <div
      v-if="['awaiting_confirmation', 'editing'].includes(action.state)"
      class="action-fields"
    >
      <label v-for="(_value, key) in draft" :key="key">
        <span>{{ key }}</span>
        <input v-model="draft[key]" :aria-label="String(key)" />
      </label>
      <button class="link-button" @click="save">Save changes</button>
    </div>
    <dl v-else>
      <template v-for="(value, key) in action.payload" :key="key">
        <dt>{{ key }}</dt>
        <dd>{{ value }}</dd>
      </template>
    </dl>

    <p v-if="action.policy_decision" class="policy-reason">
      Policy: {{ action.policy_decision.reason }}
    </p>
    <div
      v-if="Array.isArray(action.payload.source_attachment_refs)"
      class="action-sources"
    >
      <span>Sources</span>
      <button
        v-for="source in action.payload.source_attachment_refs"
        :key="source"
        class="link-button"
        @click="emit('openAttachment', String(source))"
      >
        Open attachment
      </button>
    </div>
    <p v-if="action.result" class="action-result">
      Result: {{ JSON.stringify(action.result) }}
    </p>
    <p v-if="action.state === 'blocked_plugin_disabled'">
      The contributing plugin is disabled. Re-enable it before revalidation.
    </p>

    <footer>
      <button
        v-if="action.state === 'awaiting_confirmation'"
        class="primary"
        @click="emit('confirm', action.id)"
      >
        Confirm
      </button>
      <button
        v-if="
          [
            'awaiting_confirmation',
            'editing',
            'blocked_plugin_disabled',
          ].includes(action.state)
        "
        @click="emit('cancel', action.id)"
      >
        Cancel
      </button>
      <button
        v-if="action.state === 'applied'"
        @click="emit('undo', action.id)"
      >
        Undo
      </button>
    </footer>
  </article>
</template>
