<script setup lang="ts">
import DOMPurify from "dompurify";
import { marked } from "marked";
import { computed } from "vue";

const props = defineProps<{ text: string }>();
const html = computed(() =>
  DOMPurify.sanitize(marked.parse(props.text, { async: false }) as string),
);
</script>

<template>
  <div class="markdown" v-html="html" />
</template>
