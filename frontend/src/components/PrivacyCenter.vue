<script setup lang="ts">
import { onMounted, ref } from "vue";
import type { AssistantApi } from "../api";
import type { PrivacyJob, PrivacyResource } from "../types";
import PrivacyJobStatus from "./PrivacyJobStatus.vue";

const props = defineProps<{ api: AssistantApi; conversationId: string }>();
const emit = defineEmits<{ close: [] }>();
const resources = ref<PrivacyResource[]>([]);
const selected = ref<string[]>([]);
const job = ref<PrivacyJob | null>(null);

onMounted(async () => {
  resources.value = await props.api.privacyResources();
});

async function exportData(): Promise<void> {
  job.value = await props.api.exportPrivacy(selected.value);
}

async function previewDeletion(): Promise<void> {
  job.value = await props.api.previewDeletion(
    selected.value,
    props.conversationId,
  );
}

async function confirmDeletion(id: string): Promise<void> {
  job.value = await props.api.confirmDeletion(id);
  resources.value = await props.api.privacyResources();
}
</script>

<template>
  <aside
    class="privacy-center"
    role="dialog"
    aria-modal="true"
    aria-label="Privacy Center"
  >
    <header class="panel-header">
      <div>
        <small>Assistant data</small>
        <h2>Privacy Center</h2>
      </div>
      <button aria-label="Close Privacy Center" @click="emit('close')">
        ×
      </button>
    </header>
    <ul class="privacy-resources">
      <li v-for="resource in resources" :key="resource.category">
        <label>
          <input
            v-model="selected"
            type="checkbox"
            :value="resource.category"
          />
          <span>
            <strong>{{ resource.category }}</strong>
            <small
              >{{ resource.count }} items · {{ resource.owner }} ·
              {{ resource.retention }}</small
            >
          </span>
        </label>
        <span v-if="!resource.deletable" class="retained">Host controlled</span>
      </li>
    </ul>
    <div class="privacy-actions">
      <button :disabled="!selected.length" @click="exportData">
        Export selected
      </button>
      <button
        class="danger"
        :disabled="!selected.length"
        @click="previewDeletion"
      >
        Delete selected
      </button>
    </div>
    <PrivacyJobStatus v-if="job" :job="job" @confirm="confirmDeletion" />
  </aside>
</template>
