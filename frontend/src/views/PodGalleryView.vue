<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="bg-white rounded-xl p-5 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div>
        <h2 class="text-sm font-semibold text-slate-900 tracking-tight">Proof of Delivery (POD) Hub</h2>
        <p class="text-xs text-slate-500">Arsip digital bukti serah terima barang: foto di lokasi, tanda tangan, dan geotag GPS</p>
      </div>
      <div class="flex items-center space-x-2">
        <button
          @click="refreshPods"
          :disabled="loading"
          class="px-3 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs font-medium text-slate-700 transition flex items-center space-x-1.5"
        >
          <RefreshCw :size="13" :class="loading ? 'animate-spin' : ''" />
          <span>{{ loading ? 'Memuat...' : 'Refresh' }}</span>
        </button>
      </div>
    </div>

    <!-- Search input -->
    <div class="bg-white rounded-xl p-4 border border-slate-200 flex justify-between items-center">
      <div class="relative w-full max-w-sm">
        <input
          v-model="searchQuery"
          @keyup.enter="refreshPods"
          type="text"
          placeholder="Cari nomor POD, Delivery Note, nama penerima..."
          class="w-full text-xs pl-8 pr-3 py-2 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:border-slate-400 transition"
        />
        <Search :size="13" class="absolute left-2.5 top-2.5 text-slate-400" />
      </div>
      <div class="text-xs text-slate-500">
        Total <strong class="text-slate-800">{{ totalCount }}</strong> Bukti POD
      </div>
    </div>

    <!-- Gallery Grid -->
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      <div
        v-for="pod in pods"
        :key="pod.name"
        class="bg-white rounded-xl border border-slate-200 overflow-hidden flex flex-col hover:border-slate-300 transition"
      >
        <!-- Photo Thumbnail -->
        <div class="aspect-4/3 bg-slate-100 overflow-hidden relative group">
          <img
            v-if="pod.proof_photo"
            :src="pod.proof_photo"
            alt="Foto Serah Terima"
            class="w-full h-full object-cover group-hover:scale-102 transition duration-200 cursor-pointer"
            @click="openImage(pod.proof_photo)"
          />
          <div v-else class="w-full h-full flex items-center justify-center text-slate-400 text-xs">
            Tanpa Foto
          </div>
          <span class="absolute top-2 left-2 px-2 py-0.5 rounded text-[10px] font-medium bg-slate-900/80 text-white backdrop-blur-xs">
            {{ pod.delivery_note }}
          </span>
        </div>

        <!-- Content -->
        <div class="p-4 flex-1 flex flex-col justify-between space-y-3">
          <div>
            <div class="flex items-start justify-between">
              <div>
                <span class="text-xs font-semibold text-slate-900 block">{{ pod.recipient_name }}</span>
                <span class="text-[11px] text-slate-500">{{ pod.recipient_relationship || 'Yang Bersangkutan' }}</span>
              </div>
              <span class="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/80">
                Verified
              </span>
            </div>

            <!-- Signature snippet -->
            <div v-if="pod.signature" class="mt-2.5 p-1.5 bg-slate-50 rounded-lg border border-slate-100 flex items-center justify-center h-12">
              <img :src="pod.signature" alt="Tanda Tangan" class="max-h-full max-w-full object-contain" />
            </div>

            <div class="text-[11px] text-slate-400 mt-2 inline-flex items-center space-x-1">
              <Calendar :size="11" class="text-slate-400" />
              <span>{{ pod.submitted_at ? pod.submitted_at.slice(0, 16) : '-' }}</span>
            </div>
          </div>

          <!-- GPS button -->
          <div class="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
            <span v-if="pod.latitude && pod.longitude" class="text-[10px] font-mono text-slate-500 inline-flex items-center space-x-1">
              <MapPin :size="11" class="text-slate-400" />
              <span>{{ Number(pod.latitude).toFixed(3) }}, {{ Number(pod.longitude).toFixed(3) }}</span>
            </span>
            <span v-else class="text-[10px] text-slate-400">No GPS</span>

            <a
              v-if="pod.latitude && pod.longitude"
              :href="`https://www.google.com/maps?q=${pod.latitude},${pod.longitude}`"
              target="_blank"
              class="text-[11px] font-medium text-emerald-700 hover:text-emerald-900 transition inline-flex items-center space-x-1"
            >
              <span>Maps</span>
              <ExternalLink :size="10" />
            </a>
          </div>
        </div>
      </div>
    </div>

    <div v-if="pods.length === 0 && !loading" class="text-center py-16 bg-white rounded-xl border border-slate-200 text-slate-400 text-xs">
      Belum ada riwayat dokumen Proof of Delivery.
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { RefreshCw, Search, Calendar, MapPin, ExternalLink } from 'lucide-vue-next'
import { DeliveryApi } from '@/api'

const loading = ref(false)
const pods = ref([])
const totalCount = ref(0)
const searchQuery = ref('')

async function refreshPods() {
  loading.value = true
  try {
    const res = await DeliveryApi.getPods({
      search: searchQuery.value,
      page: 1,
      page_size: 40
    })
    pods.value = res.items || []
    totalCount.value = res.total_count || 0
  } catch (err) {
    console.error('POD load err:', err)
  } finally {
    loading.value = false
  }
}

function openImage(url) {
  if (url) window.open(url, '_blank')
}

onMounted(() => {
  refreshPods()
})
</script>