<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="bg-white rounded-xl p-5 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div>
        <h2 class="text-sm font-semibold text-slate-900 tracking-tight">Rute Pengiriman (Delivery Trips)</h2>
        <p class="text-xs text-slate-500">Manajemen rute multi-drop armada sendiri, jadwal berangkat, dan progres antar</p>
      </div>
      <div class="flex items-center space-x-2">
        <button
          @click="refreshTrips"
          :disabled="loading"
          class="px-3 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs font-medium text-slate-700 transition flex items-center space-x-1.5"
        >
          <RefreshCw :size="13" :class="loading ? 'animate-spin' : ''" />
          <span>{{ loading ? 'Memuat...' : 'Refresh' }}</span>
        </button>
        <button
          @click="openNewTripModal"
          class="px-3.5 py-2 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-medium transition flex items-center space-x-1.5"
        >
          <Plus :size="14" />
          <span>Buat Trip Baru</span>
        </button>
      </div>
    </div>

    <!-- Status Filter & Search -->
    <div class="bg-white rounded-xl p-4 border border-slate-200 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
      <div class="flex items-center space-x-1 bg-slate-100 p-1 rounded-lg text-xs font-medium text-slate-600">
        <button
          v-for="tab in statusTabs"
          :key="tab.id"
          @click="changeTab(tab.id)"
          :class="[
            'px-3 py-1.5 rounded-md transition',
            currentTab === tab.id ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'hover:text-slate-900'
          ]"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="relative w-full md:w-64">
        <input
          v-model="searchQuery"
          @keyup.enter="refreshTrips"
          type="text"
          placeholder="Cari ID trip, driver, plat nomor..."
          class="w-full text-xs pl-8 pr-3 py-2 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:border-slate-400 transition"
        />
        <Search :size="13" class="absolute left-2.5 top-2.5 text-slate-400" />
      </div>
    </div>

    <!-- Trips Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="trip in trips"
        :key="trip.name"
        class="bg-white rounded-xl border border-slate-200 hover:border-slate-300 transition p-5 flex flex-col justify-between"
      >
        <div>
          <!-- Card Header -->
          <div class="flex justify-between items-start mb-3">
            <div>
              <span class="text-xs font-semibold text-slate-900">{{ trip.name }}</span>
              <div class="text-[11px] text-slate-400 mt-0.5 inline-flex items-center space-x-1">
                <Calendar :size="11" class="text-slate-400" />
                <span>{{ trip.departure_time ? trip.departure_time.slice(0, 16) : 'Hari Ini' }}</span>
              </div>
            </div>
            <span
              :class="[
                'px-2 py-0.5 rounded text-[10px] font-medium border uppercase',
                trip.status === 'Completed' ? 'bg-emerald-50 text-emerald-700 border-emerald-200/80' :
                trip.status === 'In Transit' ? 'bg-blue-50 text-blue-700 border-blue-200/80' :
                trip.status === 'Scheduled' ? 'bg-amber-50 text-amber-700 border-amber-200/80' :
                'bg-slate-100 text-slate-700 border-slate-200'
              ]"
            >
              {{ trip.status }}
            </span>
          </div>

          <!-- Driver & Vehicle Details -->
          <div class="p-3 bg-slate-50/80 border border-slate-100 rounded-lg space-y-1.5 text-xs text-slate-700 mb-4">
            <div class="flex items-center space-x-2">
              <span class="text-slate-400 text-[11px]">Driver:</span>
              <span class="font-medium text-slate-800">{{ trip.driver_name || trip.driver }}</span>
            </div>
            <div class="flex items-center space-x-2">
              <span class="text-slate-400 text-[11px]">Armada:</span>
              <span class="font-medium text-slate-700">{{ trip.vehicle }}</span>
            </div>
          </div>

          <!-- Progress Bar -->
          <div class="space-y-1.5 mb-4">
            <div class="flex justify-between items-center text-xs">
              <span class="text-slate-500 font-medium">Progres Antar</span>
              <span class="font-semibold text-slate-800">
                {{ trip.completed_stops }} / {{ trip.total_stops }} Stop ({{ Math.round((trip.completed_stops / Math.max(1, trip.total_stops)) * 100) }}%)
              </span>
            </div>
            <div class="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
              <div
                class="bg-sky-500 h-1.5 rounded-full transition-all duration-300"
                :style="{ width: `${(trip.completed_stops / Math.max(1, trip.total_stops)) * 100}%` }"
              ></div>
            </div>
          </div>

          <!-- Stops Snippet -->
          <div class="space-y-1 text-xs mb-4">
            <span class="text-[10px] uppercase font-semibold text-slate-400 tracking-wider block">Titik Singgah (Stops):</span>
            <div
              v-for="(stop, idx) in trip.stops.slice(0, 3)"
              :key="idx"
              class="flex items-center space-x-2 text-slate-600 truncate"
            >
              <span :class="['w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-semibold', stop.visited ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-600']">
                <Check v-if="stop.visited" :size="9" />
                <span v-else>{{ idx + 1 }}</span>
              </span>
              <span class="truncate">{{ stop.customer }}</span>
            </div>
            <div v-if="trip.stops.length > 3" class="text-[11px] text-slate-400 pl-6">
              + {{ trip.stops.length - 3 }} stop lainnya
            </div>
          </div>
        </div>

        <!-- Card Footer Actions -->
        <div class="pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
          <div class="flex items-center space-x-1">
            <button
              v-if="trip.status === 'Scheduled' || trip.status === 'Draft'"
              @click="startTrip(trip.name)"
              class="px-2.5 py-1.5 bg-sky-600 hover:bg-sky-700 text-white font-medium rounded-lg transition inline-flex items-center space-x-1"
            >
              <Play :size="11" />
              <span>Mulai</span>
            </button>
            <button
              v-if="trip.status === 'In Transit'"
              @click="completeTrip(trip.name)"
              class="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg transition inline-flex items-center space-x-1"
            >
              <Check :size="11" />
              <span>Selesai</span>
            </button>
          </div>

          <div class="flex items-center space-x-1.5">
            <a
              :href="`/driver?trip=${trip.name}`"
              target="_blank"
              class="px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium transition inline-flex items-center space-x-1"
              title="Buka Navigator Supir di Handphone"
            >
              <Smartphone :size="12" />
              <span>Navigator</span>
            </a>
            <button
              @click="openTripDetail(trip)"
              class="px-2.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-white font-medium rounded-lg transition"
            >
              Detail Rute
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="trips.length === 0 && !loading" class="text-center py-16 bg-white rounded-xl border border-slate-200 text-slate-400 text-xs">
      Tidak ada Delivery Trip yang ditemukan.
    </div>

    <!-- Modals -->
    <CreateTripModal
      :is-open="isNewTripModalOpen"
      :initial-notes="[]"
      :drivers="driverList"
      :vehicles="vehicleList"
      @close="isNewTripModalOpen = false"
      @created="refreshTrips"
    />

    <!-- Trip Detail Slide-Over -->
    <div v-if="selectedTripDetail" class="fixed inset-0 z-50 overflow-hidden">
      <div @click="selectedTripDetail = null" class="absolute inset-0 bg-slate-950/50 backdrop-blur-xs transition-opacity"></div>
      <div class="fixed inset-y-0 right-0 pl-10 max-w-full flex">
        <div class="w-screen max-w-xl bg-white shadow-xl flex flex-col border-l border-slate-200">
          <!-- Drawer Header -->
          <div class="p-6 bg-slate-900 text-white flex items-center justify-between">
            <div>
              <span class="text-[10px] uppercase tracking-wider text-slate-400 font-medium">Detail Rute Armada</span>
              <h2 class="text-base font-semibold tracking-tight mt-0.5">{{ selectedTripDetail.name }}</h2>
            </div>
            <button @click="selectedTripDetail = null" class="text-slate-400 hover:text-white p-1.5 rounded-lg transition">
              <X :size="16" />
            </button>
          </div>

          <!-- Drawer Body -->
          <div class="flex-1 p-6 space-y-6 overflow-y-auto text-xs text-slate-700">
            <!-- Summary card -->
            <div class="grid grid-cols-2 gap-3 p-4 bg-slate-50 border border-slate-200 rounded-lg">
              <div>
                <span class="text-slate-400 block text-[11px]">Pengemudi (Driver):</span>
                <span class="font-semibold text-slate-900 text-sm">{{ selectedTripDetail.driver_name || selectedTripDetail.driver }}</span>
              </div>
              <div>
                <span class="text-slate-400 block text-[11px]">Kendaraan:</span>
                <span class="font-semibold text-slate-900 text-sm">{{ selectedTripDetail.vehicle }}</span>
              </div>
            </div>

            <!-- Stops Timeline -->
            <div>
              <h4 class="font-semibold text-slate-900 uppercase tracking-wider text-[11px] mb-3 flex items-center space-x-1.5">
                <MapPin :size="13" class="text-slate-500" />
                <span>Urutan Titik Antar / Multi-Drop</span>
              </h4>

              <div class="space-y-3">
                <div
                  v-for="(stop, idx) in selectedTripDetail.delivery_stops"
                  :key="idx"
                  class="p-4 rounded-lg border border-slate-200 bg-white hover:border-slate-300 transition"
                >
                  <div class="flex items-start justify-between">
                    <div class="flex items-start space-x-3">
                      <span :class="['w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold text-white flex-shrink-0', stop.visited ? 'bg-emerald-500' : 'bg-sky-600']">
                        <Check v-if="stop.visited" :size="12" />
                        <span v-else>{{ idx + 1 }}</span>
                      </span>
                      <div>
                        <div class="font-semibold text-slate-900 text-sm">{{ stop.customer }}</div>
                        <div class="text-slate-500 text-[11px] mt-0.5">{{ stop.customer_address || '-' }}</div>
                        <div class="text-[11px] text-slate-400 mt-1">
                          Dokumen: <strong class="text-slate-700 font-medium">{{ stop.delivery_note }}</strong>
                        </div>
                      </div>
                    </div>

                    <span
                      :class="[
                        'px-2 py-0.5 rounded text-[10px] font-medium uppercase border',
                        stop.visited ? 'bg-emerald-50 text-emerald-700 border-emerald-200/80' : 'bg-slate-100 text-slate-600 border-slate-200'
                      ]"
                    >
                      {{ stop.visited ? 'Terkirim' : 'Menunggu' }}
                    </span>
                  </div>

                  <!-- POD Info if visited -->
                  <div v-if="stop.pod" class="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px]">
                    <span class="text-emerald-700 font-medium">
                      Diterima oleh: <strong class="font-semibold">{{ stop.pod.recipient_name }}</strong> ({{ stop.pod.recipient_relationship || 'Yang Bersangkutan' }})
                    </span>
                    <a
                      v-if="stop.pod.proof_photo"
                      :href="stop.pod.proof_photo"
                      target="_blank"
                      class="text-sky-600 font-medium hover:underline inline-flex items-center space-x-1"
                    >
                      <span>Lihat Foto POD</span>
                      <ExternalLink :size="10" />
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Drawer Footer -->
          <div class="p-4 bg-slate-50 border-t border-slate-200 flex justify-between items-center">
            <a
              :href="`/app/delivery-trip/${selectedTripDetail.name}`"
              target="_blank"
              class="px-3 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 text-xs font-medium transition inline-flex items-center space-x-1"
            >
              <span>Buka di ERPNext Desk</span>
              <ExternalLink :size="11" />
            </a>
            <div class="flex items-center space-x-2">
              <a
                :href="`/driver?trip=${selectedTripDetail.name}`"
                target="_blank"
                class="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-medium transition inline-flex items-center space-x-1.5"
              >
                <Smartphone :size="12" />
                <span>Buka di Navigator Supir</span>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import {
  RefreshCw,
  Plus,
  Search,
  Calendar,
  Check,
  Play,
  Smartphone,
  X,
  MapPin,
  ExternalLink
} from 'lucide-vue-next'
import { DeliveryApi } from '@/api'
import CreateTripModal from '@/components/CreateTripModal.vue'

const loading = ref(false)
const trips = ref([])
const totalCount = ref(0)
const currentPage = ref(1)
const currentTab = ref('All')
const searchQuery = ref('')

const driverList = ref([])
const vehicleList = ref([])

const isNewTripModalOpen = ref(false)
const selectedTripDetail = ref(null)

const statusTabs = [
  { id: 'All', label: 'Semua Rute' },
  { id: 'In Transit', label: 'Sedang Berjalan' },
  { id: 'Scheduled', label: 'Terjadwal' },
  { id: 'Completed', label: 'Selesai' },
]

async function refreshTrips() {
  loading.value = true
  try {
    const res = await DeliveryApi.getTrips({
      status_filter: currentTab.value === 'All' ? null : currentTab.value,
      search: searchQuery.value,
      page: currentPage.value,
      page_size: 20
    })
    trips.value = res.items || []
    totalCount.value = res.total_count || 0
  } catch (err) {
    console.error('Failed to load trips:', err)
  } finally {
    loading.value = false
  }
}

async function loadFleet() {
  try {
    const res = await DeliveryApi.getFleetResources()
    driverList.value = res.drivers || []
    vehicleList.value = res.vehicles || []
  } catch (e) {
    console.error('Fleet res err:', e)
  }
}

function changeTab(tabId) {
  currentTab.value = tabId
  refreshTrips()
}

function openNewTripModal() {
  isNewTripModalOpen.value = true
}

async function openTripDetail(trip) {
  try {
    const detail = await DeliveryApi.getTripDetail(trip.name)
    selectedTripDetail.value = detail
  } catch (err) {
    alert('Gagal memuat detail trip: ' + err.message)
  }
}

async function startTrip(name) {
  if (!confirm(`Mulai perjalanan trip ${name}?`)) return
  try {
    await DeliveryApi.startTrip(name)
    refreshTrips()
  } catch (err) {
    alert(err.message)
  }
}

async function completeTrip(name) {
  if (!confirm(`Selesaikan perjalanan trip ${name}? Semua pengiriman akan ditandai rampung.`)) return
  try {
    await DeliveryApi.completeTrip(name)
    refreshTrips()
  } catch (err) {
    alert(err.message)
  }
}

onMounted(() => {
  refreshTrips()
  loadFleet()
})
</script>