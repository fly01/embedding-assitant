<script setup lang="ts">
import { onMounted, ref } from "vue";
import type { AssistantApi } from "../api";
import type { MemoryRecord } from "../types";

const props = defineProps<{ api: AssistantApi; conversationId: string }>();
const emit = defineEmits<{ close: [] }>();
const memories = ref<MemoryRecord[]>([]);
const content = ref("");
const scope = ref<"conversation" | "app" | "user">("conversation");

async function load(): Promise<void> {
  memories.value = await props.api.listMemory(props.conversationId);
}

async function add(): Promise<void> {
  await props.api.createMemory({
    conversation_id:
      scope.value === "conversation" ? props.conversationId : undefined,
    scope: scope.value,
    content: content.value,
  });
  content.value = "";
  await load();
}

async function remove(id: string): Promise<void> {
  await props.api.deleteMemory(id);
  await load();
}

onMounted(load);
</script>

<template>
  <aside
    class="memory-panel"
    role="dialog"
    aria-modal="true"
    aria-label="Memory"
  >
    <header class="panel-header">
      <h2>Memory</h2>
      <button aria-label="Close Memory" @click="emit('close')">×</button>
    </header>
    <form class="memory-form" @submit.prevent="add">
      <input
        v-model="content"
        aria-label="Memory content"
        placeholder="Remember a verified preference"
        required
      />
      <select v-model="scope" aria-label="Memory scope">
        <option value="conversation">Conversation</option>
        <option value="app">Application</option>
        <option value="user">User</option>
      </select>
      <button class="primary" type="submit">Remember</button>
    </form>
    <ul class="memory-list">
      <li v-for="memory in memories" :key="memory.id">
        <span
          ><strong>{{ memory.scope }}</strong
          >{{ memory.content }}</span
        >
        <button
          :aria-label="`Delete memory ${memory.content}`"
          @click="remove(memory.id)"
        >
          Delete
        </button>
      </li>
    </ul>
  </aside>
</template>
