<script setup lang="ts">
import type { AssistantEvent, DisclosureLevel } from "../types";

defineProps<{
  level: DisclosureLevel;
  status: string;
  summary: string;
  rawTrace: string;
  developerEvents: AssistantEvent[];
}>();
</script>

<template>
  <section
    v-if="level !== 'hidden' && (status || summary || rawTrace)"
    class="thinking-disclosure"
  >
    <div v-if="status" class="thinking-status">
      <span class="pulse" />{{ status }}
    </div>
    <details
      v-if="summary && ['activity', 'developer', 'raw_trace'].includes(level)"
    >
      <summary>Reasoning summary</summary>
      <p>{{ summary }}</p>
    </details>
    <details v-if="level === 'raw_trace' && rawTrace" class="raw-trace">
      <summary>Sensitive provider trace</summary>
      <p>{{ rawTrace }}</p>
    </details>
    <details
      v-if="
        ['developer', 'raw_trace'].includes(level) && developerEvents.length
      "
    >
      <summary>Developer events · {{ developerEvents.length }}</summary>
      <ol class="developer-events">
        <li v-for="event in developerEvents" :key="event.event_id">
          #{{ event.seq }} {{ event.type }}
        </li>
      </ol>
    </details>
  </section>
</template>
