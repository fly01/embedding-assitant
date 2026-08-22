<script setup lang="ts">
import { onMounted, watch, type Component } from "vue";
import type { AssistantApi } from "../api";
import type { DictationAdapter } from "../dictation";
import { createAssistantStore } from "../store";
import Composer from "./Composer.vue";
import ConversationThread from "./ConversationThread.vue";
import ThinkingDisclosure from "./ThinkingDisclosure.vue";
import ToolActivity from "./ToolActivity.vue";

const props = defineProps<{
  api: AssistantApi;
  conversationId: string;
  dictationAdapter: DictationAdapter;
  renderers?: Record<string, Component>;
}>();
const emit = defineEmits<{ hostRefresh: [] }>();
const store = createAssistantStore(props.api);

watch(
  () => props.conversationId,
  (id) => store.loadConversation(id),
);
watch(
  () => store.state.actions.map((action) => action.state),
  (states, previous) => {
    if (
      states.some(
        (state, index) =>
          state === "applied" && previous?.[index] !== "applied",
      )
    )
      emit("hostRefresh");
  },
);
onMounted(() => store.loadConversation(props.conversationId));
</script>

<template>
  <main class="assistant-shell">
    <header class="assistant-toolbar">
      <div class="assistant-title">
        <span class="assistant-mark">F</span>
        <div><strong>Assistant</strong><small>Framed by the Host</small></div>
      </div>
      <div class="assistant-settings">
        <label>
          <span>Context</span>
          <select
            v-model="store.state.contextProfile"
            aria-label="Context profile"
          >
            <option value="lite">Lite</option>
            <option value="balanced">Balanced</option>
            <option value="durable">Durable</option>
          </select>
        </label>
        <label>
          <span>Execution</span>
          <select
            v-model="store.state.executionMode"
            aria-label="Execution mode"
          >
            <option value="read_only">Read only</option>
            <option value="confirm_each">Confirm each</option>
            <option value="auto_apply_allowlist">Auto allowlist</option>
          </select>
        </label>
        <label>
          <span>Disclosure</span>
          <select
            v-model="store.state.disclosureLevel"
            aria-label="Disclosure level"
          >
            <option value="hidden">Hidden</option>
            <option value="status">Status</option>
            <option value="contextual">Contextual</option>
            <option value="activity">Activity</option>
            <option value="developer">Developer</option>
            <option value="raw_trace">Raw trace</option>
          </select>
        </label>
      </div>
    </header>
    <ConversationThread :api="api" :store="store" :renderers="renderers" />
    <div class="run-details">
      <ThinkingDisclosure
        :level="store.state.disclosureLevel"
        :status="store.state.thinking"
        :summary="store.state.reasoningSummary"
        :raw-trace="store.state.rawTrace"
        :developer-events="store.state.developerEvents"
      />
      <ToolActivity :items="store.state.tools" />
      <ul v-if="store.state.citations.length" class="citations">
        <li
          v-for="citation in store.state.citations"
          :key="citation.document_id"
        >
          <a
            v-if="citation.source_url"
            :href="citation.source_url"
            target="_blank"
            rel="noreferrer"
            >{{ citation.title }}</a
          >
          <span v-else>{{ citation.title }}</span>
        </li>
      </ul>
      <p v-if="store.state.error" class="error-banner" role="alert">
        {{ store.state.error }}
      </p>
      <div class="run-controls">
        <button v-if="store.state.streaming" @click="store.stop">Stop</button>
        <button
          v-else-if="
            store.state.messages.some((message) => message.role === 'user')
          "
          @click="store.regenerate"
        >
          Regenerate
        </button>
      </div>
    </div>
    <Composer :store="store" :dictation-adapter="dictationAdapter" />
  </main>
</template>
