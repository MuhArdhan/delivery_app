<template>
  <div class="space-y-4">
    <!-- Header with Search & Filters -->
    <div class="bg-white rounded-xl p-5 border border-slate-200 space-y-4">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 class="text-sm font-semibold text-slate-900 tracking-tight">Daftar Pengiriman (Delivery Notes)</h2>
          <p class="text-xs text-slate-500">Kelola dan jadwalkan pengiriman ke kurir 3PL atau armada multi-drop internal</p>
        </div>
        <div class="flex items-center space-x-2">
          <button
            @click="refreshNotes"
            :disabled="loading"
            class="px-3 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs font-medium text-slate-700 transition flex items-center space-x-1.5"
          >
            <RefreshCw :size="13" :class="loading ? 'animate-spin' : ''" />
            <span>{{ loading ? 'Memuat...' : 'Refresh' }}</span>
          </button>
          <button
            @click="openBatchTripModal"
            :disabled="selectedNotes.length === 0"
            class="px-3.5 py-2 rounded-lg bg-sky-600 hover:bg-sky-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-medium transition flex items-center space-x-1.5"
          >
            <Route :size="14" />
            <span>Buat Delivery Trip ({{ selectedNotes.length }})</span>
          </button>
        </div>
      </div>

      <!-- Filter Controls -->
      <div class="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 pt-3 border-t border-slate-100">
        <!-- Status Tabs -->
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

        <!-- Search input & Method Filter -->
        <div class="flex items-center space-x-2">
          <select
            v-model="methodFilter"
            @change="refreshNotes"
            class="text-xs px-3 py-2 rounded-lg border border-slate-200 bg-white text-slate-700 focus:outline-none focus:border-slate-400"
          >
            <option value="All">Semua Metode</option>
            <option value="Armada Sendiri">Armada Sendiri</option>
            <option value="Ekspedisi">Ekspedisi (3PL)</option>
          </select>

          <div class="relative w-full md:w-64">
            <input
              v-model="searchQuery"
              @keyup.enter="refreshNotes"
              type="text"
              placeholder="Cari order, pelanggan, resi..."
              class="w-full text-xs pl-8 pr-3 py-2 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:border-slate-400 transition"
            />
            <Search :size="13" class="absolute left-2.5 top-2.5 text-slate-400" />
          </div>
        </div>
      </div>
    </div>

    <!-- Multi-select Sticky Bar (appears when items are selected) -->
    <div
      v-if="selectedNotes.length > 0"
      class="bg-slate-900 text-white px-5 py-3 rounded-xl shadow-lg flex items-center justify-between border border-slate-800"
    >
      <div class="flex items-center space-x-3 text-xs">
        <span class="w-5 h-5 rounded-md bg-sky-500 text-white font-semibold flex items-center justify-center text-[10px]">
          {{ selectedNotes.length }}
        </span>
        <span class="font-medium">{{ selectedNotes.length }} Pengiriman Dipilih untuk Dijadwalkan</span>
      </div>
      <div class="flex items-center space-x-2">
        <button
          @click="selectedNotes = []"
          class="px-3 py-1.5 rounded-lg text-slate-400 hover:text-white text-xs font-medium transition"
        >
          Batal Pilih
        </button>
        <button
          @click="openBatchTripModal"
          class="px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium transition flex items-center space-x-1.5"
        >
          <Route :size="14" />
          <span>Rencanakan Delivery Trip Sekarang</span>
        </button>
      </div>
    </div>

    <!-- Delivery Notes Table -->
    <div class="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-xs">
          <thead class="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
            <tr>
              <th class="p-3.5 w-10 text-center">
                <input
                  type="checkbox"
                  :checked="isAllSelected"
                  @change="toggleSelectAll"
                  class="rounded border-slate-300 text-sky-600 focus:ring-0 w-3.5 h-3.5 cursor-pointer"
                />
              </th>
              <th class="p-3.5">Dokumen / Tanggal</th>
              <th class="p-3.5">Tujuan & Pelanggan</th>
              <th class="p-3.5">Barang & Nilai</th>
              <th class="p-3.5">Metode Kirim</th>
              <th class="p-3.5">Status Pelacakan / Trip</th>
              <th class="p-3.5 text-right">Aksi Dispatch</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr
              v-for="note in notes"
              :key="note.name"
              :class="[
                'hover:bg-slate-50 transition cursor-pointer',
                isSelected(note) ? 'bg-sky-50/40' : ''
              ]"
              @click="openDrawer(note)"
            >
              <!-- Checkbox -->
              <td class="p-3.5 text-center" @click.stop>
                <input
                  type="checkbox"
                  :value="note"
                  v-model="selectedNotes"
                  :disabled="note.custom_delivery_method === 'Ekspedisi' || note.trip"
                  class="rounded border-slate-300 text-sky-600 focus:ring-0 w-3.5 h-3.5 cursor-pointer disabled:opacity-30"
                />
              </td>

              <!-- Document Name & Date -->
              <td class="p-3.5">
                <div class="font-semibold text-slate-900 hover:text-sky-600 transition">{{ note.name }}</div>
                <div class="text-[11px] text-slate-400 mt-0.5 inline-flex items-center space-x-1">
                  <Calendar :size="11" class="text-slate-400" />
                  <span>{{ note.posting_date }}</span>
                </div>
              </td>

              <!-- Customer & Destination -->
              <td class="p-3.5 max-w-xs">
                <div class="font-semibold text-slate-800 truncate">{{ note.customer_name || note.customer }}</div>
                <div class="text-[11px] text-slate-500 line-clamp-2 mt-0.5 leading-snug">
                  {{ note.address_display || note.shipping_address || '-' }}
                </div>
              </td>

              <!-- Items & Total -->
              <td class="p-3.5">
                <div class="font-semibold text-slate-900">
                  Rp {{ Number(note.grand_total || 0).toLocaleString('id-ID') }}
                </div>
                <div class="text-[11px] text-slate-500 mt-0.5">
                  <span class="font-medium">{{ note.items?.length || 1 }} jenis item</span>
                  <span> ({{ note.total_qty || 0 }} qty)</span>
                </div>
              </td>

              <!-- Method -->
              <td class="p-3.5">
                <span
                  :class="[
                    'inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium border',
                    note.custom_delivery_method === 'Ekspedisi'
                      ? 'bg-indigo-50 text-indigo-700 border-indigo-200/80'
                      : 'bg-sky-50 text-sky-700 border-sky-200/80'
                  ]"
                >
                  <component :is="note.custom_delivery_method === 'Ekspedisi' ? Send : Truck" :size="12" />
                  <span>{{ note.custom_delivery_method || 'Armada Sendiri' }}</span>
                </span>
              </td>

              <!-- Status & Trip info -->
              <td class="p-3.5">
                <!-- If Ekspedisi -->
                <div v-if="note.custom_delivery_method === 'Ekspedisi'">
                  <div class="flex items-center space-x-1.5">
                    <span class="font-semibold text-slate-800 uppercase">{{ note.custom_courier_code || '3PL' }}</span>
                    <span
                      v-if="note.custom_tracking_status"
                      :class="[
                        'px-2 py-0.5 rounded text-[10px] font-medium border',
                        note.custom_tracking_status === 'Delivered'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200/80'
                          : 'bg-blue-50 text-blue-700 border-blue-200/80'
                      ]"
                    >
                      {{ note.custom_tracking_status }}
                    </span>
                  </div>
                  <div v-if="note.custom_waybill_no" class="font-mono text-[11px] text-slate-500 mt-0.5">
                    Resi: {{ note.custom_waybill_no }}
                  </div>
                  <div v-else class="text-[10px] text-amber-600 font-medium mt-0.5">
                    Belum input resi
                  </div>
                </div>

                <!-- If Armada Sendiri -->
                <div v-else>
                  <div v-if="note.trip" class="flex items-center space-x-1.5">
                    <span class="font-medium text-sky-700 bg-sky-50 px-2 py-0.5 rounded border border-sky-200 text-[10px]">
                      {{ note.trip.trip_name }}
                    </span>
                    <span
                      :class="[
                        'px-1.5 py-0.5 rounded text-[10px] font-medium border',
                        note.custom_pod_status === 'Delivered'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200/80'
                          : 'bg-slate-100 text-slate-700 border-slate-200'
                      ]"
                    >
                      {{ note.custom_pod_status || 'Dalam Rute' }}
                    </span>
                  </div>
                  <div v-else-if="note.custom_pod_status === 'Delivered'" class="text-emerald-600 font-medium flex items-center space-x-1">
                    <Check :size="12" />
                    <span>Terkirim (POD)</span>
                  </div>
                  <div v-else class="text-slate-400 text-[11px]">
                    Belum dijadwalkan
                  </div>
                </div>
              </td>

              <!-- Action Buttons -->
              <td class="p-3.5 text-right space-x-1" @click.stop>
                <!-- Ekspedisi Dispatch Button -->
                <button
                  v-if="note.custom_delivery_method !== 'Ekspedisi' && !note.trip"
                  @click="openDispatchEkspedisi(note)"
                  class="px-2.5 py-1 rounded-md border border-indigo-200 bg-indigo-50/70 hover:bg-indigo-100 text-indigo-700 font-medium transition text-[11px] inline-flex items-center space-x-1"
                  title="Kirim menggunakan kurir pihak ketiga (Biteship)"
                >
                  <Send :size="11" />
                  <span>Ekspedisi</span>
                </button>

                <!-- Single Trip Add Button -->
                <button
                  v-if="note.custom_delivery_method !== 'Ekspedisi' && !note.trip"
                  @click="openSingleTripModal(note)"
                  class="px-2.5 py-1 rounded-md border border-sky-200 bg-sky-50/70 hover:bg-sky-100 text-sky-700 font-medium transition text-[11px] inline-flex items-center space-x-1"
                  title="Tugaskan ke Armada Sendiri"
                >
                  <Truck :size="11" />
                  <span>Trip</span>
                </button>

                <!-- Tracking Button -->
                <button
                  v-if="note.custom_waybill_no"
                  @click="openTrackingModal(note)"
                  class="px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-medium transition text-[11px] inline-flex items-center space-x-1"
                  title="Lacak Riwayat Resi"
                >
                  <Search :size="11" />
                  <span>Lacak</span>
                </button>

                <!-- POD Button -->
                <button
                  v-if="note.custom_proof_of_delivery || note.custom_pod_status === 'Delivered'"
                  @click="openPodModal(note)"
                  class="px-2.5 py-1 rounded-md border border-emerald-200 bg-emerald-50 text-emerald-700 font-medium transition text-[11px] inline-flex items-center space-x-1"
                  title="Lihat Bukti Pengiriman POD"
                >
                  <ShieldCheck :size="11" />
                  <span>POD</span>
                </button>
              </td>
            </tr>

            <tr v-if="notes.length === 0 && !loading">
              <td colspan="7" class="py-12 text-center text-slate-400 text-xs">
                Tidak ada Delivery Note yang sesuai dengan kriteria filter.
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="p-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
        <div>
          Menampilkan <strong class="text-slate-800">{{ notes.length }}</strong> dari <strong class="text-slate-800">{{ totalCount }}</strong> Pengiriman
        </div>
        <div class="flex items-center space-x-2">
          <button
            @click="prevPage"
            :disabled="currentPage <= 1 || loading"
            class="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition font-medium inline-flex items-center space-x-1"
          >
            <ChevronLeft :size="13" />
            <span>Sebelumnya</span>
          </button>
          <span class="px-2 text-slate-700 font-semibold">Hal. {{ currentPage }}</span>
          <button
            @click="nextPage"
            :disabled="notes.length < pageSize || loading"
            class="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition font-medium inline-flex items-center space-x-1"
          >
            <span>Selanjutnya</span>
            <ChevronRight :size="13" />
          </button>
        </div>
      </div>
    </div>

    <!-- Modals & Drawers -->
    <DispatchEkspedisiModal
      :is-open="isEkspedisiModalOpen"
      :note="activeNote"
      :couriers="courierList"
      @close="isEkspedisiModalOpen = false"
      @dispatched="handleDispatched"
    />

    <CreateTripModal
      :is-open="isTripModalOpen"
      :initial-notes="tripInitialNotes"
      :drivers="driverList"
      :vehicles="vehicleList"
      @close="isTripModalOpen = false"
      @created="handleTripCreated"
    />

    <TrackingTimelineModal
      :is-open="isTrackingModalOpen"
      :note="activeNote"
      @close="isTrackingModalOpen = false"
    />

    <PodDetailModal
      :is-open="isPodModalOpen"
      :note="activeNote"
      :pod="activePod"
      @close="isPodModalOpen = false"
    />

    <DeliveryNoteDrawer
      :is-open="isDrawerOpen"
      :note="drawerNote"
      @close="isDrawerOpen = false"
      @dispatch-ekspedisi="openDispatchEkspedisi"
      @add-to-trip="openSingleTripModal"
      @track="openTrackingModal"
      @view-pod="openPodModal"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  RefreshCw,
  Route,
  Search,
  Calendar,
  Send,
  Truck,
  Check,
  ShieldCheck,
  ChevronLeft,
  ChevronRight
} from 'lucide-vue-next'
import { DeliveryApi } from '@/api'
import DispatchEkspedisiModal from '@/components/DispatchEkspedisiModal.vue'
import CreateTripModal from '@/components/CreateTripModal.vue'
import TrackingTimelineModal from '@/components/TrackingTimelineModal.vue'
import PodDetailModal from '@/components/PodDetailModal.vue'
import DeliveryNoteDrawer from '@/components/DeliveryNoteDrawer.vue'

const loading = ref(false)
const notes = ref([])
const totalCount = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const currentTab = ref('Ready')
const methodFilter = ref('All')
const searchQuery = ref('')

const selectedNotes = ref([])
const activeNote = ref(null)
const activePod = ref(null)
const drawerNote = ref(null)

const isEkspedisiModalOpen = ref(false)
const isTripModalOpen = ref(false)
const isTrackingModalOpen = ref(false)
const isPodModalOpen = ref(false)
const isDrawerOpen = ref(false)

const tripInitialNotes = ref([])
const driverList = ref([])
const vehicleList = ref([])
const courierList = ref([])

const statusTabs = [
  { id: 'Ready', label: 'Siap Kirim' },
  { id: 'In Transit', label: 'Dalam Pengiriman' },
  { id: 'Delivered', label: 'Terkirim (Selesai)' },
  { id: 'All', label: 'Semua' },
]

const isAllSelected = computed(() => {
  const eligible = notes.value.filter(n => n.custom_delivery_method !== 'Ekspedisi' && !n.trip)
  return eligible.length > 0 && selectedNotes.value.length === eligible.length
})

function isSelected(note) {
  return selectedNotes.value.some(n => n.name === note.name)
}

function toggleSelectAll() {
  const eligible = notes.value.filter(n => n.custom_delivery_method !== 'Ekspedisi' && !n.trip)
  if (isAllSelected.value) {
    selectedNotes.value = []
  } else {
    selectedNotes.value = [...eligible]
  }
}

function changeTab(tabId) {
  currentTab.value = tabId
  currentPage.value = 1
  refreshNotes()
}

async function refreshNotes() {
  loading.value = true
  try {
    const res = await DeliveryApi.getNotes({
      status_filter: currentTab.value === 'All' ? null : currentTab.value,
      method_filter: methodFilter.value === 'All' ? null : methodFilter.value,
      search: searchQuery.value,
      page: currentPage.value,
      page_size: pageSize.value
    })
    notes.value = res.items || []
    totalCount.value = res.total_count || 0
  } catch (err) {
    console.error('Failed to load notes:', err)
  } finally {
    loading.value = false
  }
}

async function loadResources() {
  try {
    const res = await DeliveryApi.getFleetResources()
    driverList.value = res.drivers || []
    vehicleList.value = res.vehicles || []
    courierList.value = res.couriers || []
  } catch (err) {
    console.error('Failed to load fleet resources:', err)
  }
}

function openDispatchEkspedisi(note) {
  activeNote.value = note
  isEkspedisiModalOpen.value = true
}

function openSingleTripModal(note) {
  tripInitialNotes.value = [note]
  isTripModalOpen.value = true
}

function openBatchTripModal() {
  if (selectedNotes.value.length === 0) return
  tripInitialNotes.value = [...selectedNotes.value]
  isTripModalOpen.value = true
}

function openTrackingModal(note) {
  activeNote.value = note
  isTrackingModalOpen.value = true
}

async function openPodModal(note) {
  activeNote.value = note
  activePod.value = null
  isPodModalOpen.value = true
  try {
    const detail = await DeliveryApi.getNoteDetail(note.name)
    activePod.value = detail.pod
  } catch (e) {
    console.error('POD load err:', e)
  }
}

async function openDrawer(note) {
  drawerNote.value = note
  isDrawerOpen.value = true
  try {
    const detail = await DeliveryApi.getNoteDetail(note.name)
    drawerNote.value = detail
  } catch (e) {
    console.error('Drawer load err:', e)
  }
}

function handleDispatched() {
  refreshNotes()
}

function handleTripCreated() {
  selectedNotes.value = []
  refreshNotes()
}

function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--
    refreshNotes()
  }
}

function nextPage() {
  if (notes.value.length >= pageSize.value) {
    currentPage.value++
    refreshNotes()
  }
}

onMounted(() => {
  loadResources()
  refreshNotes()
})
</script>