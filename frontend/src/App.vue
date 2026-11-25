<script setup>
import { ref, onMounted } from 'vue'
const sources = ref([])
onMounted(async () => { sources.value = await (await fetch('/api/sources')).json() })
</script>
<template>
  <h1>PoniaMDM</h1>
  <ul><li v-for="s in sources" :key="s.key">{{ s.label }}</li></ul>
</template>
