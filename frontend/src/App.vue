<script setup lang="ts">
import { onMounted, ref } from "vue";
import { AssistantApi } from "./api";
import AssistantShell from "./components/AssistantShell.vue";
import MemoryPanel from "./components/MemoryPanel.vue";
import PrivacyCenter from "./components/PrivacyCenter.vue";
import type { ComposerToolbarPlacement } from "./composer";
import { DemoDictationAdapter } from "./dictation";
import type { Conversation, HostRecord } from "./types";

const api = new AssistantApi(
  import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000",
  "demo-user",
  "reference-host",
);
const dictationAdapter = new DemoDictationAdapter();
const conversations = ref<Conversation[]>([]);
const conversationId = ref("");
const hostRecords = ref<HostRecord[]>([]);
const privacyOpen = ref(false);
const memoryOpen = ref(false);
const composerToolbarPlacement = ref<ComposerToolbarPlacement>("below");

async function loadConversations(): Promise<void> {
  conversations.value = await api.listConversations();
  if (!conversations.value.length)
    conversations.value = [await api.createConversation("Main")];
  if (!conversationId.value) conversationId.value = conversations.value[0].id;
}

async function createConversation(): Promise<void> {
  const conversation = await api.createConversation(
    `Conversation ${conversations.value.length + 1}`,
  );
  conversations.value.unshift(conversation);
  conversationId.value = conversation.id;
}

async function refreshRecords(): Promise<void> {
  hostRecords.value = await api.listHostRecords();
}

onMounted(async () => {
  await Promise.all([loadConversations(), refreshRecords()]);
});
</script>

<template>
  <div class="reference-host">
    <header class="host-header">
      <div>
        <small>Reference Host</small>
        <h1>Framed Assistant</h1>
      </div>
      <nav aria-label="Host conversation navigation">
        <select v-model="conversationId" aria-label="Active conversation">
          <option
            v-for="conversation in conversations"
            :key="conversation.id"
            :value="conversation.id"
          >
            {{ conversation.title }}
          </option>
        </select>
        <button @click="createConversation">New conversation</button>
        <select
          v-model="composerToolbarPlacement"
          aria-label="Composer toolbar placement"
        >
          <option value="below">Toolbar below</option>
          <option value="side">Toolbar side</option>
        </select>
        <button @click="memoryOpen = true">Memory</button>
        <button @click="privacyOpen = true">Privacy</button>
      </nav>
    </header>
    <div class="host-layout">
      <AssistantShell
        v-if="conversationId"
        :api="api"
        :conversation-id="conversationId"
        :dictation-adapter="dictationAdapter"
        :composer-toolbar-placement="composerToolbarPlacement"
        @host-refresh="refreshRecords"
      />
      <aside class="host-records">
        <header>
          <div>
            <small>Host-owned data</small>
            <h2>Records</h2>
          </div>
          <button @click="refreshRecords">Refresh</button>
        </header>
        <ul>
          <li v-for="record in hostRecords" :key="record.id">
            <strong>{{ record.title }}</strong>
            <span>{{ record.amount.toFixed(2) }}</span>
            <small>{{ record.id }} · v{{ record.version }}</small>
          </li>
        </ul>
        <p v-if="!hostRecords.length">No Host records yet.</p>
      </aside>
    </div>
    <PrivacyCenter
      v-if="privacyOpen && conversationId"
      :api="api"
      :conversation-id="conversationId"
      @close="privacyOpen = false"
    />
    <MemoryPanel
      v-if="memoryOpen && conversationId"
      :api="api"
      :conversation-id="conversationId"
      @close="memoryOpen = false"
    />
  </div>
</template>
