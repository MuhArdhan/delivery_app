<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="bg-white rounded-xl p-5 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div>
        <h2 class="text-sm font-semibold text-slate-900 tracking-tight">Perjalanan</h2>
        <p class="text-xs text-slate-500">Manajemen rute multi-drop armada sendiri, jadwal berangkat, dan monitoring progres checkpoint</p>
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
    <div v-if="error" role="alert" class="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{{ error }} <button @click="refreshTrips" class="underline">Coba lagi</button></div>
    <div class="flex flex-wrap items-center gap-3 text-sm">
      <select v-model="companyFilter" @change="currentPage = 1; refreshTrips()" aria-label="Filter company" class="max-w-full rounded-lg border border-slate-200 bg-white p-2">
        <option value="">Semua company</option>
        <option v-for="company in companies" :key="company.name" :value="company.name">{{ company.company_name || company.name }}</option>
      </select>
      <span class="text-xs text-slate-500">{{ updatedAt ? `Data diperbarui pukul ${updatedAt}` : 'Data belum dimuat' }} · otomatis 30 detik</span>
    </div>
    <div class="bg-white rounded-xl p-4 border border-slate-200 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
      <div class="flex flex-wrap gap-1 bg-slate-100 p-1 rounded-lg text-xs font-medium text-slate-600">
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

      <div class="relative w-full md:w-72">
        <input
          v-model="searchQuery"
          @keyup.enter="currentPage = 1; refreshTrips()"
          type="text"
          placeholder="Cari ID trip, driver, plat nomor..."
          class="w-full text-xs pl-8 pr-3 py-2 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:border-slate-400 transition"
        />
        <Search :size="13" class="absolute left-2.5 top-2.5 text-slate-400" />
      </div>
    </div>

    <!-- Empty State -->
    <p v-if="loading || loadingDetail" role="status" class="text-sm text-slate-500">{{ loadingDetail ? 'Memuat detail perjalanan...' : 'Memperbarui perjalanan...' }}</p>
    <div v-if="!loading && trips.length === 0" class="bg-white rounded-xl border border-slate-200 p-12 text-center">
      <p class="text-sm font-medium text-slate-700">Tidak ada Delivery Trip ditemukan</p>
      <p class="text-xs text-slate-400 mt-1">Coba sesuaikan kata kunci pencarian atau buat trip pengiriman baru.</p>
    </div>

    <TripMonitoringTable v-if="trips.length" class="hidden md:block" :trips="trips" @select="openTripDetail" @depart="confirmDeparture" />
    <!-- Compact cards retain readability on small screens. -->
    <div v-if="trips.length" class="grid grid-cols-1 md:hidden gap-4">
      <div
        v-for="trip in trips"
        :key="trip.name"
        class="bg-white rounded-xl border border-slate-200 hover:border-slate-300 transition p-5 flex flex-col justify-between shadow-xs"
      >
        <div>
          <!-- Card Header -->
          <div class="flex justify-between items-start mb-3">
            <div>
              <div class="flex items-center space-x-1.5">
                <span class="text-xs font-bold text-slate-900">{{ trip.name }}</span>
                <span v-if="trip.company" class="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-medium">
                  {{ trip.company }}
                </span>
              </div>
              <div class="text-[11px] text-slate-400 mt-0.5 flex items-center space-x-1">
                <Calendar :size="11" class="text-slate-400" />
                <span>Rencana: {{ trip.departure_time ? trip.departure_time.slice(0, 16) : 'Hari Ini' }}</span>
              </div>
            </div>
            <span
              :class="[
                'px-2 py-0.5 rounded text-[10px] font-semibold border uppercase',
                getMonitoringStatusBadgeClass(trip.monitoring_status || trip.status)
              ]"
            >
              {{ trip.monitoring_status || trip.status }}
            </span>
          </div>

          <!-- Driver & Vehicle Details -->
          <div class="p-3 bg-slate-50/80 border border-slate-100 rounded-lg space-y-1.5 text-xs text-slate-700 mb-3">
            <div class="flex items-center justify-between">
              <span class="text-slate-400 text-[11px]">Pengemudi:</span>
              <span class="font-medium text-slate-800">{{ trip.driver_name || trip.driver }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-slate-400 text-[11px]">Armada:</span>
              <span class="font-medium text-slate-700">{{ trip.vehicle }}</span>
            </div>
            <div class="flex items-center justify-between pt-1 border-t border-slate-200/60">
              <span class="text-slate-400 text-[11px]">Berangkat Aktual:</span>
              <span :class="['font-medium', trip.custom_actual_departure ? 'text-slate-800' : 'text-amber-600']">
                {{ trip.custom_actual_departure ? trip.custom_actual_departure.slice(0, 16) : 'Belum Berangkat' }}
              </span>
            </div>
          </div>

          <!-- Progress Bar -->
          <div class="space-y-1.5 mb-3">
            <div class="flex justify-between items-center text-xs">
              <span class="text-slate-500 font-medium">Progres Kunjungan</span>
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

          <!-- Checkpoint & Next Stop Info -->
          <div class="p-2.5 bg-slate-50 rounded-lg border border-slate-100 text-[11px] space-y-1 mb-3">
            <div class="flex items-center justify-between">
              <span class="text-slate-400">Checkpoint Terakhir:</span>
              <span class="font-medium text-slate-700 truncate max-w-[170px]" :title="trip.last_checkpoint?.text">
                {{ trip.last_checkpoint?.text || 'Belum ada' }}
              </span>
            </div>
            <div class="flex items-center justify-between" v-if="trip.next_planned_stop">
              <span class="text-slate-400">Tujuan Berikutnya (rencana):</span>
              <span class="font-medium text-sky-700 truncate max-w-[170px]">
                {{ trip.next_planned_stop.customer }}
              </span>
            </div>
          </div>

          <!-- Coordinate warning if any -->
          <div v-if="trip.unlocated_stops > 0" class="mb-3 text-[11px] text-amber-700 bg-amber-50 px-2 py-1 rounded border border-amber-200 flex items-center justify-between">
            <span>{{ trip.unlocated_stops }} titik belum ada koordinat</span>
          </div>

          <!-- Stops Snippet -->
          <div class="space-y-1 text-xs mb-4">
            <span class="text-[10px] uppercase font-semibold text-slate-400 tracking-wider block">Urutan Singgah (Stops):</span>
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
          <div class="flex items-center space-x-1.5">
            <button
              v-if="trip.docstatus === 1 && !trip.custom_actual_departure && trip.status !== 'Completed'"
              @click="confirmDeparture(trip.name)"
              class="px-2.5 py-1.5 bg-sky-600 hover:bg-sky-700 text-white font-medium rounded-lg transition inline-flex items-center space-x-1"
            >
              <Play :size="11" />
              <span>Berangkat</span>
            </button>
            <button
              v-if="trip.status === 'In Transit'"
              @click="handleCompleteTrip(trip)"
              class="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg transition inline-flex items-center space-x-1"
            >
              <Check :size="11" />
              <span>Selesai</span>
            </button>
          </div>

          <div class="flex items-center space-x-1.5">
            <button
              @click="openTripDetail(trip)"
              class="px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 font-medium transition inline-flex items-center space-x-1"
            >
              <span>Detail & Rute</span>
              <ChevronRight :size="11" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Slide-over Drawer for Trip Details -->
    <div class="flex items-center justify-end gap-3 text-sm">
      <button :disabled="currentPage === 1 || loading" @click="currentPage--; refreshTrips()" class="disabled:opacity-40">Sebelumnya</button>
      <span>{{ currentPage }} / {{ Math.max(1, Math.ceil(totalCount / 20)) }}</span>
      <button :disabled="currentPage * 20 >= totalCount || loading" @click="currentPage++; refreshTrips()" class="disabled:opacity-40">Berikutnya</button>
    </div>
    <div v-if="selectedTripDetail" class="fixed inset-0 z-50 overflow-hidden bg-slate-950/60 backdrop-blur-xs flex justify-end">
      <div class="relative w-full max-w-2xl bg-white shadow-2xl flex flex-col h-full transform transition-all border-l border-slate-200">
        <!-- Drawer Header -->
        <div class="bg-slate-900 text-white p-5 flex items-center justify-between border-b border-slate-800">
          <div>
            <div class="flex items-center space-x-2">
              <h3 class="font-bold text-base text-white">{{ selectedTripDetail.name }}</h3>
              <span
                :class="[
                  'px-2 py-0.5 rounded text-[10px] font-semibold uppercase border',
                  getMonitoringStatusBadgeClass(selectedTripDetail.monitoring_status || selectedTripDetail.status)
                ]"
              >
                {{ selectedTripDetail.monitoring_status || selectedTripDetail.status }}
              </span>
            </div>
            <p class="text-xs text-slate-400 mt-0.5">Company: {{ selectedTripDetail.company }} | Rute Multi-Drop Armada Sendiri</p>
          </div>
          <button @click="closeTripDetail" aria-label="Tutup detail perjalanan" class="text-slate-400 hover:text-white p-1.5 rounded-lg transition">
            <X :size="16" />
          </button>
        </div>

        <!-- Drawer Body -->
        <div class="flex-1 p-5 space-y-5 overflow-y-auto text-xs text-slate-700">
          <!-- Summary card -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 bg-slate-50 border border-slate-200 rounded-lg">
            <div>
              <span class="text-slate-400 block text-[10px] uppercase font-semibold">Pengemudi:</span>
              <span class="font-semibold text-slate-900 text-xs">{{ selectedTripDetail.driver_name || selectedTripDetail.driver }}</span>
            </div>
            <div>
              <span class="text-slate-400 block text-[10px] uppercase font-semibold">Armada:</span>
              <span class="font-semibold text-slate-900 text-xs">{{ selectedTripDetail.vehicle }}</span>
            </div>
            <div>
              <span class="text-slate-400 block text-[10px] uppercase font-semibold">Jadwal Berangkat:</span>
              <span class="font-semibold text-slate-900 text-xs">{{ selectedTripDetail.departure_time ? selectedTripDetail.departure_time.slice(0, 16) : '-' }}</span>
            </div>
            <div>
              <span class="text-slate-400 block text-[10px] uppercase font-semibold">Berangkat Aktual:</span>
              <span :class="['font-semibold text-xs', selectedTripDetail.custom_actual_departure ? 'text-slate-900' : 'text-amber-600']">
                {{ selectedTripDetail.custom_actual_departure ? selectedTripDetail.custom_actual_departure.slice(0, 16) : 'Belum' }}
              </span>
            </div>
          </div>

          <!-- Planned Road Route Map -->
          <div>
            <div class="flex items-center justify-between mb-2">
              <h4 class="font-semibold text-slate-900 uppercase tracking-wider text-[11px] flex items-center space-x-1.5">
                <MapPin :size="13" class="text-sky-600" />
                <span>Peta Rute Rencana Jalan (OSRM)</span>
              </h4>
              <button
                type="button"
                @click="reloadTripRoute"
                :disabled="loadingRoute"
                class="text-[11px] text-sky-600 hover:text-sky-800 font-medium inline-flex items-center space-x-1"
              >
                <RefreshCw :size="11" :class="loadingRoute ? 'animate-spin' : ''" />
                <span>Hitung Ulang Jalur</span>
              </button>
            </div>

            <div class="h-[420px] rounded-lg overflow-hidden border border-slate-200">
              <OperationsMap
                :markers="drawerMapMarkers"
                :route-polyline="selectedTripDetail.route?.route_points || []"
                :route-info="selectedTripDetail.route || null"
                @retry-route="reloadTripRoute"
              />
            </div>
          </div>

          <!-- Checkpoint Progress Indicator -->
          <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between">
            <div>
              <span class="text-slate-400 text-[10px] uppercase font-semibold block">Progres Antar</span>
              <span class="font-bold text-slate-900 text-sm">
                {{ selectedTripDetail.completed_stops }} / {{ selectedTripDetail.delivery_stops?.length || 0 }} Stop Dikunjungi
              </span>
            </div>
            <div class="text-right">
              <span class="text-slate-400 text-[10px] uppercase font-semibold block">Checkpoint Terakhir</span>
              <span class="font-medium text-slate-800 text-xs">
                {{ selectedTripDetail.last_checkpoint?.text || 'Belum ada checkpoint' }}
              </span>
            </div>
          </div>

          <!-- Stops Timeline & Notes -->
          <div>
            <h4 class="font-semibold text-slate-900 uppercase tracking-wider text-[11px] mb-3 flex items-center space-x-1.5">
              <Route :size="13" class="text-slate-500" />
              <span>Urutan Titik Antar / Multi-Drop</span>
            </h4>

            <div class="space-y-3">
              <div
                v-for="stop in selectedTripDetail.delivery_stops"
                :key="stop.idx"
                class="p-4 rounded-lg border border-slate-200 bg-white hover:border-slate-300 transition"
              >
                <div class="flex items-start justify-between">
                  <div class="flex items-start space-x-3">
                    <span :class="['w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold text-white flex-shrink-0', stop.visited ? 'bg-emerald-500' : 'bg-sky-600']">
                      <Check v-if="stop.visited" :size="12" />
                      <span v-else>{{ stop.idx }}</span>
                    </span>
                    <div>
                      <div class="font-semibold text-slate-900 text-sm">{{ stop.customer }}</div>
                      <div class="text-slate-500 text-[11px] mt-0.5">{{ stop.customer_address || '-' }}</div>
                      <div class="text-[11px] text-slate-400 mt-1 flex items-center space-x-2">
                        <span>DN: <strong class="text-slate-700 font-medium">{{ stop.delivery_note }}</strong></span>
                        <span v-if="stop.has_coordinates" class="text-emerald-700 font-medium">({{ stop.lat }}, {{ stop.lng }})</span>
                        <span v-else class="text-amber-600">Koordinat belum diatur</span>
                      </div>
                    </div>
                  </div>

                  <span
                    :class="[
                      'px-2 py-0.5 rounded text-[10px] font-medium uppercase border',
                      stop.visited ? 'bg-emerald-50 text-emerald-700 border-emerald-200/80' : 'bg-slate-100 text-slate-600 border-slate-200'
                    ]"
                  >
                    {{ stop.visited ? 'Dikunjungi' : 'Belum Dikunjungi' }}
                  </span>
                </div>

                <!-- Confirmation Status info from Scanner App -->
                <div v-if="stop.visited" class="mt-2.5 pt-2 border-t border-slate-100 text-[11px] flex items-center justify-between text-slate-600">
                  <span class="inline-flex items-center space-x-1 text-emerald-700 font-medium">
                    <Check :size="11" />
                    <span>{{ stop.confirmation_text || 'Dikunjungi' }}</span>
                  </span>
                  <span v-if="stop.scanned_by_name" class="text-slate-400 text-[10px]">
                    Petugas: {{ stop.scanned_by_name }}
                  </span>
                </div>

                <!-- Operational Notes / Delivery Obstacles (Kendala Pengantaran) -->
                <div class="mt-3 pt-2.5 border-t border-slate-100">
                  <div class="flex items-center justify-between">
                    <span class="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                      Catatan Kendala / Operasional:
                    </span>
                    <button
                      type="button"
                      @click="toggleEditDetails(stop)"
                      class="text-[10px] text-sky-600 hover:text-sky-800 font-medium"
                    >
                      {{ editingStopIdx === stop.idx ? 'Batal' : (stop.details ? 'Ubah Catatan' : '+ Tambah Catatan') }}
                    </button>
                  </div>

                  <!-- Read Mode -->
                  <div v-if="editingStopIdx !== stop.idx" class="mt-1 text-[11px] text-slate-600">
                    <p v-if="stop.details" class="bg-slate-50 p-2 rounded border border-slate-100 leading-relaxed">
                      {{ stop.details }}
                    </p>
                    <span v-else class="text-slate-400 italic">Belum ada catatan kendala pengantaran.</span>
                  </div>

                  <!-- Edit Mode -->
                  <div v-else class="mt-2 space-y-2">
                    <textarea
                      v-model="stopDetailsInput"
                      rows="2"
                      placeholder="Tulis kendala pengantaran atau catatan operasional di sini..."
                      class="w-full text-xs p-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400"
                    ></textarea>
                    <div class="flex justify-end space-x-1.5">
                      <button
                        type="button"
                        @click="editingStopIdx = null"
                        class="px-2.5 py-1 rounded text-slate-600 hover:bg-slate-100 text-[11px]"
                      >
                        Batal
                      </button>
                      <button
                        type="button"
                        @click="saveStopDetails(stop)"
                        :disabled="savingStopDetails"
                        class="px-3 py-1 rounded bg-sky-600 hover:bg-sky-700 text-white text-[11px] font-medium"
                      >
                        {{ savingStopDetails ? 'Menyimpan...' : 'Simpan Catatan' }}
                      </button>
                    </div>
                  </div>
                </div>

                <!-- POD Info if available -->
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
            <!-- Aksi Berangkat if not yet departed -->
            <button
              v-if="selectedTripDetail.docstatus === 1 && !selectedTripDetail.custom_actual_departure && selectedTripDetail.status !== 'Completed'"
              @click="confirmDeparture(selectedTripDetail.name)"
              class="px-3.5 py-2 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-medium transition inline-flex items-center space-x-1.5"
            >
              <Play :size="12" />
              <span>Konfirmasi Berangkat</span>
            </button>

            <!-- Aksi Selesai if in transit -->
            <button
              v-if="selectedTripDetail.status === 'In Transit'"
              @click="handleCompleteTrip(selectedTripDetail)"
              class="px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium transition inline-flex items-center space-x-1.5"
            >
              <Check :size="12" />
              <span>Selesaikan Trip</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Trip Modal -->
    <CreateTripModal
      :is-open="isNewTripModalOpen"
      :initial-notes="[]"
      :drivers="driverList"
      :vehicles="vehicleList"
      @close="isNewTripModalOpen = false"
      @created="refreshTrips"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  RefreshCw,
  Plus,
  Search,
  Calendar,
  Check,
  Play,
  X,
  MapPin,
  ExternalLink,
  ChevronRight,
  Route
} from 'lucide-vue-next'
import { DeliveryApi } from '@/api'
import { useVisibleRefresh } from '@/composables/useVisibleRefresh'
import CreateTripModal from '@/components/CreateTripModal.vue'
import OperationsMap from '@/components/OperationsMap.vue'
import TripMonitoringTable from '@/components/TripMonitoringTable.vue'

const loading = ref(false)
const trips = ref([])
const totalCount = ref(0)
const currentPage = ref(1)
const currentTab = ref('All')
const searchQuery = ref('')
const companyFilter = ref('')
const companies = ref([])
const error = ref('')
const updatedAt = ref('')
const loadingDetail = ref(false)
let detailVersion = 0
let refreshQueued = false

const driverList = ref([])
const vehicleList = ref([])

const isNewTripModalOpen = ref(false)
const selectedTripDetail = ref(null)
const loadingRoute = ref(false)

// Edit stop details
const editingStopIdx = ref(null)
const stopDetailsInput = ref('')
const savingStopDetails = ref(false)

const statusTabs = [
  { id: 'All', label: 'Semua Rute' },
  { id: 'In Transit', label: 'Dalam Perjalanan' },
  { id: 'Scheduled', label: 'Terjadwal' },
  { id: 'Completed', label: 'Selesai Kunjungan' },
]

function getMonitoringStatusBadgeClass(status) {
  if (status === 'Dalam Perjalanan' || status === 'In Transit') {
    return 'bg-blue-50 text-blue-700 border-blue-200/80'
  }
  if (status === 'Selesai Kunjungan' || status === 'Completed') {
    return 'bg-emerald-50 text-emerald-700 border-emerald-200/80'
  }
  if (status === 'Terjadwal' || status === 'Scheduled') {
    return 'bg-amber-50 text-amber-700 border-amber-200/80'
  }
  if (status === 'Dibatalkan' || status === 'Cancelled') {
    return 'bg-rose-50 text-rose-700 border-rose-200/80'
  }
  return 'bg-slate-100 text-slate-700 border-slate-200'
}

const drawerMapMarkers = computed(() => {
  if (!selectedTripDetail.value) return []
  const markers = []

  // Origin marker
  if (selectedTripDetail.value.has_origin_coordinates) {
    markers.push({
      id: `ORIGIN-${selectedTripDetail.value.company}`,
      type: 'origin',
      customer: `Gudang: ${selectedTripDetail.value.company}`,
      address: selectedTripDetail.value.company,
      lat: selectedTripDetail.value.origin_lat,
      lng: selectedTripDetail.value.origin_lng,
      status: 'Asal Keberangkatan',
      method: 'Armada Sendiri'
    })
  }

  // Stop markers
  ;(selectedTripDetail.value.delivery_stops || []).forEach((stop) => {
    if (stop.has_coordinates) {
      markers.push({
        id: stop.delivery_note || `${selectedTripDetail.value.name}-stop-${stop.idx}`,
        idx: stop.idx,
        stop_number: stop.idx,
        type: 'stop',
        customer: stop.customer,
        address: stop.customer_address,
        lat: stop.lat,
        lng: stop.lng,
        visited: Boolean(stop.visited),
        status: stop.visited ? 'Terkirim' : 'Dalam Pengiriman',
        confirmed_at_text: stop.confirmation_text || (stop.visited ? 'Dikunjungi' : null),
        method: 'Armada Sendiri'
      })
    }
  })

  return markers
})

async function refreshTrips() {
  if (loading.value) { refreshQueued = true; return }
  loading.value = true
  error.value = ''
  try {
    const res = await DeliveryApi.getTrips({
      status_filter: currentTab.value === 'All' ? null : currentTab.value,
      search: searchQuery.value,
      company_filter: companyFilter.value || null,
      page: currentPage.value,
      page_size: 20
    })
    trips.value = res.items || []
    totalCount.value = res.total_count || 0
    if (selectedTripDetail.value && editingStopIdx.value === null && !savingStopDetails.value) {
      const name = selectedTripDetail.value.name
      const detail = await DeliveryApi.getTripDetail(name, false)
      if (selectedTripDetail.value?.name === name && editingStopIdx.value === null && !savingStopDetails.value) {
        selectedTripDetail.value = { ...detail, route: selectedTripDetail.value.route }
      }
    }
    updatedAt.value = new Date().toLocaleTimeString('id-ID')
  } catch (err) {
    error.value = err.message || 'Gagal memuat perjalanan. Data sebelumnya tetap ditampilkan.'
  } finally {
    loading.value = false
    if (refreshQueued) { refreshQueued = false; refreshTrips() }
  }
}

async function loadFleet() {
  try {
    const res = await DeliveryApi.getFleetResources()
    driverList.value = res.drivers || []
    vehicleList.value = res.vehicles || []
    companies.value = res.companies || []
  } catch (e) {
    console.error('Fleet res err:', e)
  }
}

function changeTab(tabId) {
  currentTab.value = tabId
  currentPage.value = 1
  refreshTrips()
}

function openNewTripModal() {
  isNewTripModalOpen.value = true
}

async function openTripDetail(trip) {
  const version = ++detailVersion
  loadingDetail.value = true
  try {
    const detail = await DeliveryApi.getTripDetail(trip.name)
    if (version === detailVersion) {
      selectedTripDetail.value = detail
      editingStopIdx.value = null
    }
  } catch (err) {
    if (version === detailVersion) error.value = 'Gagal memuat detail trip: ' + err.message
  } finally {
    if (version === detailVersion) loadingDetail.value = false
  }
}

function closeTripDetail() {
  detailVersion++
  loadingDetail.value = false
  selectedTripDetail.value = null
  editingStopIdx.value = null
}

async function reloadTripRoute() {
  if (!selectedTripDetail.value) return
  const name = selectedTripDetail.value.name
  const version = detailVersion
  loadingRoute.value = true
  try {
    const res = await DeliveryApi.getTripRoute(name)
    if (version === detailVersion && selectedTripDetail.value?.name === name) selectedTripDetail.value.route = res
  } catch (err) {
    alert('Gagal menghitung rute: ' + err.message)
  } finally {
    loadingRoute.value = false
  }
}

function toggleEditDetails(stop) {
  if (editingStopIdx.value === stop.idx) {
    editingStopIdx.value = null
  } else {
    editingStopIdx.value = stop.idx
    stopDetailsInput.value = stop.details || ''
  }
}

async function saveStopDetails(stop) {
  if (!selectedTripDetail.value) return
  savingStopDetails.value = true
  try {
    await DeliveryApi.updateStopDetails(
      selectedTripDetail.value.name,
      stop.idx,
      stopDetailsInput.value
    )
    stop.details = stopDetailsInput.value
    editingStopIdx.value = null
  } catch (err) {
    alert(err.message || 'Gagal menyimpan catatan kendala')
  } finally {
    savingStopDetails.value = false
  }
}

async function confirmDeparture(name) {
  if (!confirm(`Konfirmasi keberangkatan untuk trip ${name}? Waktu keberangkatan server akan dicatat.`)) return
  try {
    await DeliveryApi.markTripDeparted(name)
    refreshTrips()
    if (selectedTripDetail.value && selectedTripDetail.value.name === name) {
      await openTripDetail({ name })
    }
  } catch (err) {
    alert(err.message || 'Gagal mengonfirmasi keberangkatan')
  }
}

async function handleCompleteTrip(trip) {
  const unvisited = (trip.stops || trip.delivery_stops || []).filter(s => !s.visited)
  if (unvisited.length > 0) {
    const force = confirm(
      `Masih ada ${unvisited.length} titik antar yang belum dikunjungi menurut checkpoint scanner.\n\n` +
      `Apakah Anda yakin ingin memaksa penyelesaian perjalanan ini dan menandai semua stop selesai?`
    )
    if (!force) return
    try {
      await DeliveryApi.completeTrip(trip.name, 1)
      refreshTrips()
      if (selectedTripDetail.value && selectedTripDetail.value.name === trip.name) {
        await openTripDetail({ name: trip.name })
      }
    } catch (err) {
      alert(err.message || 'Gagal menyelesaikan trip')
    }
    return
  }

  if (!confirm(`Selesaikan perjalanan trip ${trip.name}? Semua titik antar telah dikunjungi.`)) return
  try {
    await DeliveryApi.completeTrip(trip.name, 0)
    refreshTrips()
    if (selectedTripDetail.value && selectedTripDetail.value.name === trip.name) {
      await openTripDetail({ name: trip.name })
    }
  } catch (err) {
    alert(err.message || 'Gagal menyelesaikan trip')
  }
}

useVisibleRefresh(refreshTrips)
onMounted(() => {
  refreshTrips()
  loadFleet()
})
</script>
