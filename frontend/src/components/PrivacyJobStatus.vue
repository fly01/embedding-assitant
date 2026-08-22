<script setup lang="ts">
import type { PrivacyJob } from "../types";

defineProps<{ job: PrivacyJob }>();
const emit = defineEmits<{ confirm: [id: string] }>();
</script>

<template>
  <section class="privacy-job" aria-live="polite">
    <header>
      <div>
        <small>{{ job.kind }}</small>
        <h3>{{ job.status.replaceAll("_", " ") }}</h3>
      </div>
      <span>{{ job.id.slice(-8) }}</span>
    </header>
    <div v-if="job.preview.impact" class="impact-list">
      <h4>Deletion impact</h4>
      <ul>
        <li v-for="item in job.preview.impact" :key="item.category">
          {{ item.category }} · {{ item.count }} · {{ item.effect ?? "delete" }}
        </li>
      </ul>
    </div>
    <button
      v-if="job.status === 'awaiting_confirmation'"
      class="danger"
      @click="emit('confirm', job.id)"
    >
      Confirm deletion
    </button>
    <ol v-if="job.results.length" class="job-results">
      <li v-for="(result, index) in job.results" :key="index">
        {{ result.category ?? result.status }} · {{ result.count ?? "" }}
      </li>
    </ol>
  </section>
</template>
