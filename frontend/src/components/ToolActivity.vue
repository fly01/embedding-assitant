<script setup lang="ts">
import type { ToolActivityItem } from "../types";

defineProps<{ items: ToolActivityItem[] }>();
</script>

<template>
  <details v-if="items.length" class="activity-panel">
    <summary>Activity · {{ items.length }}</summary>
    <ol>
      <li v-for="item in items" :key="item.name">
        <span>{{ item.name }}</span>
        <strong :class="`status-${item.status}`">{{ item.status }}</strong>
      </li>
    </ol>
  </details>
</template>
