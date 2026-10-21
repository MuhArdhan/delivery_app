<template>
  <div class="space-y-6">
    <!-- Top KPI Grid -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- 1. Siap Kirim -->
      <div class="bg-white rounded-xl p-5 border border-slate-200 flex items-center justify-between">
        <div>
          <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Siap Kirim</span>
          <span class="text-2xl font-bold text-slate-900 tracking-tight mt-1.5 block">
            {{ kpi.pending_orders || 0 }}
          </span>
          <span class="text-[11px] text-amber-600 font-medium mt-1 inline-flex items-center space-x-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
            <span>Perlu dijadwalkan</span>
          </span>
        </div>
        <div class="w-11 h-11 rounded-lg bg-amber-50 border border-amber-200/60 flex items-center justify-center text-amber-600">
          <Package :size="20" />
        </div>
      </div>

      <!-- 2. Trip Berjalan -->
      <div class="bg-white rounded-xl p-5 border border-slate-200 flex items-center justify-between">
        <div>
          <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Trip Berjalan</span>
          <span class="text-2xl font-bold text-slate-900 tracking-tight mt-1.5 block">
            {{ kpi.active_trips || 0 }}
          </span>
          <span class="text-[11px] text-sky-600 font-medium mt-1 inline-flex items-center space-x-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-sky-500"></span>
            <span>Armada Internal</span>
          </span>
        </div>
        <div class="w-11 h-11 rounded-lg bg-sky-50 border border-sky-200/60 flex items-center justify-center text-sky-600">
          <Truck :size="20" />
        </div>
      </div>

      <!-- 3. Ekspedisi In-Transit -->
      <div class="bg-white rounded-xl p-5 border border-slate-200 flex items-center justify-between">
        <div>
          <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Ekspedisi In-Transit</span>
          <span class="text-2xl font-bold text-slate-900 tracking-tight mt-1.5 block">
            {{ kpi.in_transit_couriers || 0 }}
          </span>
          <span class="text-[11px] text-indigo-600 font-medium mt-1 inline-flex items-center space-x-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-indigo-500"></span>
            <span>Biteship Live Track</span>
          </span>
        </div>
        <div class="w-11 h-11 rounded-lg bg-indigo-50 border border-indigo-200/60 flex items-center justify-center text-indigo-600">
          <Send :size="20" />
        </div>
      </div>

      <!-- 4. Terkirim Hari Ini -->
      <div class="bg-white rounded-xl p-5 border border-slate-200 flex items-center justify-between">
        <div>
          <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Terkirim Hari Ini</span>
          <span class="text-2xl font-bold text-slate-900 tracking-tight mt-1.5 block">
            {{ kpi.delivered_today || 0 }}
          </span>
          <span class="text-[11px] text-emerald-600 font-medium mt-1 inline-flex items-center space-x-1.5">
            <Check :size="12" class="text-emerald-600" />
            <span>POD Terverifikasi</span>
          </span>
        </div>
        <div class="w-11 h-11 rounded-lg bg-emerald-50 border border-emerald-200/60 flex items-center justify-center text-emerald-600">
          <CheckCircle2 :size="20" />
        </div>
      </div>
    </div>

    <!-- Main Map & Activity Split -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Operations Map (2 Cols) -->
      <div class="lg:col-span-2 bg-white rounded-xl p-5 border border-slate-200 flex flex-col space-y-3">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2.5">
            <div class="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-600">
              <MapPin :size="16" />
            </div>
            <div>
              <h3 class="font-semibold text-sm text-slate-900">Peta Sebaran Pengiriman Live</h3>
              <p class="text-xs text-slate-400">Monitoring titik antar dan status armada wilayah operasional</p>
            </div>
          </div>
          <div class="flex items-center space-x-2">
            <span v-if="unlocatedCount > 0" class="text-[11px] text-amber-700 bg-amber-50 px-2 py-1 rounded border border-amber-200">
              {{ unlocatedCount }} titik belum diatur
            </span>
            <button
              @click="refreshData"
              :disabled="loading"
              class="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-600 hover:bg-slate-50 transition"
            >
              <RefreshCw :size="13" :class="loading ? 'animate-spin' : ''" />
              <span>{{ loading ? 'Memuat...' : 'Refresh' }}</span>
            </button>
          </div>
        </div>

        <div class="flex-1 min-h-[420px] rounded-lg overflow-hidden border border-slate-100">
          <OperationsMap
            :markers="mapMarkers"
            @select-marker="handleMarkerSelect"
          />
        </div>
      </div>

      <!-- Recent Live Activity (1 Col) -->
      <div class="bg-white rounded-xl p-5 border border-slate-200 flex flex-col">
        <div class="flex items-center space-x-2.5 mb-4">
          <div class="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-600">
            <Activity :size="16" />
          </div>
          <div>
            <h3 class="font-semibold text-sm text-slate-900">Aktivitas Terkini</h3>
            <p class="text-xs text-slate-400">Pergerakan trip dan submit bukti POD terbaru</p>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto space-y-2.5 pr-1 max-h-[380px]">
          <div
            v-for="(act, idx) in activityLog"
            :key="idx"
            class="p-3 rounded-lg border border-slate-100 bg-slate-50/70 hover:bg-slate-50 transition flex items-start space-x-3 text-xs"
          >
            <div class="w-7 h-7 rounded-md bg-white border border-slate-200 flex items-center justify-center flex-shrink-0 text-slate-600">
              <component :is="act.type === 'trip' ? Route : ShieldCheck" :size="14" />
            </div>
            <div class="min-w-0 flex-1">
              <div class="flex justify-between items-center">
                <span class="font-semibold text-slate-800 truncate">{{ act.title }}</span>
                <span class="text-[10px] text-slate-400">{{ act.time }}</span>
              </div>
              <p class="text-[11px] text-slate-500 mt-0.5 line-clamp-2">{{ act.description }}</p>
              <div class="mt-1.5 flex items-center space-x-2">
                <span
                  :class="[
                    'px-2 py-0.5 rounded text-[10px] font-medium border',
                    act.status === 'Completed' || act.status === 'Submitted'
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200/60'
                      : 'bg-sky-50 text-sky-700 border-sky-200/60'
                  ]"
                >
                  {{ act.status }}
                </span>
                <a
                  v-if="act.link"
                  :href="act.link"
                  class="inline-flex items-center space-x-1 text-[10px] text-sky-600 hover:text-sky-800 font-medium"
                >
                  <span>Lihat</span>
                  <ExternalLink :size="10" />
                </a>
              </div>
            </div>
          </div>

          <div v-if="activityLog.length === 0" class="text-center py-12 text-slate-400 text-xs">
            Belum ada log pergerakan baru hari ini.
          </div>
        </div>

        <!-- Quick Action Footer -->
        <div class="border-t border-slate-100 pt-3 mt-3 grid grid-cols-2 gap-2">
          <button
            @click="$emit('nav', 'notes')"
            class="w-full py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-medium transition flex items-center justify-center space-x-1.5"
          >
            <span>Daftar Order</span>
            <ArrowRight :size="13" />
          </button>
          <button
            @click="$emit('nav', 'trips')"
            class="w-full py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-medium transition flex items-center justify-center space-x-1.5"
          >
            <span>Delivery Trips</span>
            <ArrowRight :size="13" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import {
  Package,
  Truck,
  Send,
  CheckCircle2,
  Check,
  MapPin,
  RefreshCw,
  Activity,
  Route,
  ShieldCheck,
  ExternalLink,
  ArrowRight
} from 'lucide-vue-next'
import OperationsMap from '@/components/OperationsMap.vue'
import { DeliveryApi } from '@/api'

const emit = defineEmits(['nav', 'open-note'])

const loading = ref(false)
const kpi = ref({})
const mapMarkers = ref([])
const unlocatedCount = ref(0)
const activityLog = ref([])

async function refreshData() {
  loading.value = true
  try {
    const res = await DeliveryApi.getSummary()
    kpi.value = res.kpi || {}
    mapMarkers.value = res.map_markers || []
    unlocatedCount.value = res.unlocated_count || 0
    activityLog.value = res.activity_log || []
  } catch (err) {
    console.error('Failed to load dashboard summary:', err)
  } finally {
    loading.value = false
  }
}

function handleMarkerSelect(marker) {
  emit('open-note', marker.id)
}

onMounted(() => {
  refreshData()
})
</script>