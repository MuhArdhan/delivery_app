<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 overflow-y-auto bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4">
    <div class="relative bg-white rounded-xl shadow-xl max-w-lg w-full border border-slate-200 overflow-hidden transform transition-all">
      <!-- Header -->
      <div class="bg-slate-900 text-white px-6 py-4 flex items-center justify-between border-b border-slate-800">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-200">
            <Search :size="15" class="text-sky-400" />
          </div>
          <div>
            <h3 class="font-semibold text-sm text-white">Lacak Resi Pengiriman</h3>
            <p class="text-xs text-slate-400">{{ note?.custom_courier_code?.toUpperCase() || 'EKSPEDISI' }} · {{ note?.custom_waybill_no || '-' }}</p>
          </div>
        </div>
        <button @click="close" class="text-slate-400 hover:text-white p-1 rounded-lg transition">
          <X :size="16" />
        </button>
      </div>

      <!-- Body -->
      <div class="p-6 max-h-[75vh] overflow-y-auto text-xs">
        <!-- Status summary banner -->
        <div class="flex items-center justify-between p-4 rounded-lg bg-slate-50 border border-slate-200 mb-6">
          <div>
            <span class="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Status Pengiriman</span>
            <div class="text-sm font-semibold text-slate-800 mt-0.5">
              {{ note?.custom_tracking_status || 'Dalam Pengiriman' }}
            </div>
            <div class="text-[11px] text-slate-400 mt-0.5">
              No. Resi: <span class="font-mono font-medium text-slate-700">{{ note?.custom_waybill_no }}</span>
            </div>
          </div>
          <div>
            <button
              @click="refreshTracking"
              :disabled="loading"
              class="px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-100 text-xs text-slate-700 font-medium transition flex items-center space-x-1.5"
            >
              <RefreshCw :size="12" :class="loading ? 'animate-spin' : ''" />
              <span>{{ loading ? 'Memperbarui...' : 'Sinkron Live' }}</span>
            </button>
          </div>
        </div>

        <!-- HTML Timeline or Parsed Events -->
        <div v-if="timelineHtml" v-html="timelineHtml" class="fleet-timeline-wrapper"></div>
        <div v-else-if="loading" class="text-center py-12 text-slate-400 text-xs">
          Memuat status live dari Biteship...
        </div>
        <div v-else class="text-center py-12 text-slate-400 text-xs">
          Belum ada riwayat pergerakan untuk resi ini.
        </div>
      </div>

      <!-- Footer -->
      <div class="bg-slate-50 px-6 py-3 border-t border-slate-200 flex justify-end">
        <button
          type="button"
          @click="close"
          class="px-4 py-2 rounded-lg text-xs font-medium bg-slate-900 hover:bg-slate-800 text-white transition"
        >
          Tutup
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Search, X, RefreshCw } from 'lucide-vue-next'
import { DeliveryApi } from '@/api'

const props = defineProps({
  isOpen: Boolean,
  note: Object
})

const emit = defineEmits(['close'])

const loading = ref(false)
const timelineHtml = ref('')

async function refreshTracking() {
  if (!props.note?.name) return
  loading.value = true
  try {
    const res = await DeliveryApi.trackWaybill(props.note.name)
    timelineHtml.value = res.timeline_html || ''
    if (res.status && props.note) {
      props.note.custom_tracking_status = res.status
    }
  } catch (err) {
    console.error('Tracking err:', err)
  } finally {
    loading.value = false
  }
}

function close() {
  emit('close')
}

watch(() => props.isOpen, (open) => {
  if (open) {
    timelineHtml.value = props.note?.custom_tracking_history_html || ''
    refreshTracking()
  }
})
</script>