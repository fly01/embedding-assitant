<script setup lang="ts">
import { computed, onMounted, watch, type Component } from "vue";
import type { AssistantApi } from "../api";
import {
  DEFAULT_COMPOSER_CAPABILITIES,
  type ComposerCapabilities,
  type ComposerToolbarPlacement,
  type ComposerVoiceToolMode,
} from "../composer";
import type { DictationAdapter } from "../dictation";
import { DEFAULT_ASSISTANT_LABELS, type AssistantLabels } from "../labels";
import { createAssistantStore } from "../store";
import Composer from "./Composer.vue";
import ConversationThread from "./ConversationThread.vue";
import ThinkingDisclosure from "./ThinkingDisclosure.vue";
import ToolActivity from "./ToolActivity.vue";

const props = withDefaults(
  defineProps<{
    api: AssistantApi;
    conversationId: string;
    dictationAdapter?: DictationAdapter;
    composerCapabilities?: Partial<ComposerCapabilities>;
    composerToolbarPlacement?: ComposerToolbarPlacement;
    composerVoiceToolMode?: ComposerVoiceToolMode;
    title?: string;
    subtitle?: string;
    showSettings?: boolean;
    labels?: Partial<AssistantLabels>;
    renderers?: Record<string, Component>;
    actionRenderers?: Record<string, Component>;
  }>(),
  {
    title: "Assistant",
    subtitle: "Framed by the Host",
    showSettings: true,
    labels: () => ({}),
    composerCapabilities: () => ({}),
    composerToolbarPlacement: "below",
    composerVoiceToolMode: "auto",
  },
);
const emit = defineEmits<{ hostRefresh: [] }>();
const store = createAssistantStore(props.api);
const uiLabels = computed(() => ({
  ...DEFAULT_ASSISTANT_LABELS,
  ...props.labels,
}));
const resolvedComposerCapabilities = computed(() => {
  const configured = {
    ...DEFAULT_COMPOSER_CAPABILITIES,
    ...props.composerCapabilities,
  };
  return {
    ...configured,
    liveDictation:
      configured.liveDictation && props.dictationAdapter?.available === true,
  };
});

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
          ["applied", "undone"].includes(state) && previous?.[index] !== state,
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
        <div>
          <strong>{{ title }}</strong>
          <small>{{ subtitle }}</small>
        </div>
      </div>
      <div v-if="showSettings" class="assistant-settings">
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
    <ConversationThread
      :api="api"
      :store="store"
      :renderers="renderers"
      :action-renderers="actionRenderers"
      :empty-label="uiLabels.emptyThread"
    />
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
        <button v-if="store.state.streaming" @click="store.stop">
          {{ uiLabels.stop }}
        </button>
        <button
          v-else-if="
            store.state.messages.some((message) => message.role === 'user')
          "
          @click="store.regenerate"
        >
          {{ uiLabels.regenerate }}
        </button>
      </div>
    </div>
    <Composer
      :api="api"
      :store="store"
      :dictation-adapter="dictationAdapter"
      :capabilities="resolvedComposerCapabilities"
      :toolbar-placement="composerToolbarPlacement"
      :voice-tool-mode="composerVoiceToolMode"
      :labels="uiLabels"
    />
  </main>
</template>
