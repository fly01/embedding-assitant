<script setup lang="ts">
defineProps<{ label: string }>();
</script>

<template>
  <div class="time-divider" role="separator" :aria-label="label">
    <span>{{ label }}</span>
  </div>
</template>
