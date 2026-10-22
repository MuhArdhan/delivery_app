<template>
  <div class="flex flex-col gap-6">
    <div class="flex flex-wrap items-center gap-3 text-sm">
      <label class="text-slate-600" for="dashboard-company">Company</label>
      <select id="dashboard-company" v-model="companyFilter" @change="changeCompany" class="min-w-0 max-w-full rounded-lg border border-slate-200 bg-white p-2">
        <option value="">Semua company</option>
        <option v-for="company in companies" :key="company.name" :value="company.name">{{ company.company_name || company.name }}</option>
      </select>
      <span class="text-xs text-slate-500">{{ updatedAt ? `Data diperbarui pukul ${updatedAt}` : 'Data belum dimuat' }} · otomatis 30 detik</span>
      <select v-model="tableStatusFilter" @change="applyFilters" aria-label="Filter status perjalanan" class="rounded-lg border border-slate-200 bg-white p-2">
        <option value="All">Semua status</option>
        <option value="In Transit">Dalam perjalanan</option>
        <option value="Scheduled">Terjadwal</option>
        <option value="Completed">Selesai kunjungan</option>
        <option value="Draft">Draft</option>
      </select>
      <input v-model="tableSearch" @keyup.enter="applyFilters" type="search" aria-label="Cari perjalanan" placeholder="Cari trip, driver, plat..." class="rounded-lg border border-slate-200 p-2 min-w-0" />
      <button @click="applyFilters" class="rounded-lg border border-slate-200 bg-white p-2 text-slate-700">Cari</button>
    </div>
    <div v-if="error" role="alert" class="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
      {{ error }} <button @click="refreshDashboard" class="ml-2 underline">Coba lagi</button>
    </div>
    <!-- Top KPI Grid: Menunggu Penjadwalan, Terjadwal, Dalam Perjalanan, Selesai Kunjungan Hari Ini -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- 1. Menunggu Penjadwalan -->
      <div class="bg-white rounded-xl p-5 border border-slate-200 flex items-center justify-between shadow-xs">
        <div>
          <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Menunggu Penjadwalan</span>
          <span class="text-2xl font-bold text-slate-900 tracking-tight mt-1.5 block">
            {{ kpi.pending_orders || 0 }}
          </span>
          <span class="text-[11px] text-amber-600 font-medium mt-1 inline-flex items-center space-x-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
            <span>DN Armada Sendiri</span>
          </span>
        </div>
        <div class="w-11 h-11 rounded-lg bg-amber-50 border border-amber-200/60 flex items-center justify-center text-amber-600">
          <Package :size="20" />
        </div>
      </div>

      <!-- 2. Terjadwal -->
      <div class="bg-white rounded-xl p-5 border border-slate-200 flex items-center justify-between shadow-xs">
        <div>
          <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Terjadwal</span>
          <span class="text-2xl font-bold text-slate-900 tracking-tight mt-1.5 block">
            {{ kpi.scheduled_trips || 0 }}
          </span>
          <span class="text-[11px] text-sky-600 font-medium mt-1 inline-flex items-center space-x-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-sky-500"></span>
            <span>Siap Berangkat</span>
          </span>
        </div>
        <div class="w-11 h-11 rounded-lg bg-sky-50 border border-sky-200/60 flex items-center justify-center text-sky-600">
          <Calendar :size="20" />
        </div>
      </div>

      <!-- 3. Dalam Perjalanan -->
      <div class="bg-white rounded-xl p-5 border border-slate-200 flex items-center justify-between shadow-xs">
        <div>
          <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Dalam Perjalanan</span>
          <span class="text-2xl font-bold text-slate-900 tracking-tight mt-1.5 block">
            {{ kpi.in_transit_trips || 0 }}
          </span>
          <span class="text-[11px] text-blue-600 font-medium mt-1 inline-flex items-center space-x-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
            <span>Armada Beroperasi</span>
          </span>
        </div>
        <div class="w-11 h-11 rounded-lg bg-blue-50 border border-blue-200/60 flex items-center justify-center text-blue-600">
          <Truck :size="20" />
        </div>
      </div>

      <!-- 4. Selesai Kunjungan Hari Ini -->
      <div class="bg-white rounded-xl p-5 border border-slate-200 flex items-center justify-between shadow-xs">
        <div>
          <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Selesai Kunjungan Hari Ini</span>
          <span class="text-2xl font-bold text-slate-900 tracking-tight mt-1.5 block">
            {{ kpi.completed_trips_today || 0 }}
          </span>
          <span class="text-[11px] text-emerald-600 font-medium mt-1 inline-flex items-center space-x-1.5">
            <Check :size="12" class="text-emerald-600" />
            <span>Berdasarkan konfirmasi scanner</span>
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
      <div class="order-2 lg:order-1 lg:col-span-2 min-w-0 bg-white rounded-xl p-4 border border-slate-200 flex flex-col space-y-3 shadow-xs">
        <div class="flex flex-wrap gap-3 items-center justify-between">
          <div class="flex items-center space-x-2.5">
            <div class="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-600">
              <MapPin :size="16" />
            </div>
            <div>
              <div class="flex items-center space-x-2">
                <h3 class="font-semibold text-sm text-slate-900">
                  {{ selectedTripDetail ? `Rute Rencana: ${selectedTripDetail.name}` : 'Peta Monitoring Operasional' }}
                </h3>
                <span v-if="selectedTripDetail" class="text-[10px] bg-sky-100 text-sky-800 font-medium px-2 py-0.5 rounded">
                  Driver: {{ selectedTripDetail.driver_name || selectedTripDetail.driver }}
                </span>
              </div>
              <p class="text-xs text-slate-400">
                {{ selectedTripDetail ? 'Jalur jalan OSRM dan urutan titik singgah pengiriman' : 'Monitoring titik antar dan status armada wilayah operasional' }}
              </p>
            </div>
          </div>

          <div class="flex items-center space-x-2">
            <button
              v-if="selectedTripDetail"
              @click="clearSelectedTrip"
              class="px-2.5 py-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-xs font-medium text-slate-700 transition"
            >
              Lihat Semua Titik
            </button>
            <span v-if="unlocatedCount > 0 && !selectedTripDetail" class="text-[11px] text-amber-700 bg-amber-50 px-2 py-1 rounded border border-amber-200">
              {{ unlocatedCount }} titik belum diatur
            </span>
            <button
              @click="refreshDashboard"
              :disabled="loading"
              class="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-600 hover:bg-slate-50 transition"
            >
              <RefreshCw :size="13" :class="loading ? 'animate-spin' : ''" />
              <span>{{ loading ? 'Memuat...' : 'Perbarui' }}</span>
            </button>
          </div>
        </div>

        <p v-if="loadingTrip" role="status" class="text-sm text-sky-700">Memuat rute perjalanan...</p>
        <p v-if="routeError" role="alert" class="text-sm text-red-700">{{ routeError }}</p>
        <p v-if="selectedTripDetail" class="text-xs text-slate-600">
          Konfirmasi terakhir yang tercatat: {{ selectedTripDetail.last_checkpoint?.text || 'Belum tersedia' }}.
          Tujuan berikutnya (rencana): {{ selectedTripDetail.next_planned_stop?.customer || 'Tidak ada' }}.
        </p>
        <div class="h-[420px] rounded-lg overflow-hidden border border-slate-100">
          <OperationsMap
            :markers="activeMapMarkers"
            :route-polyline="activeRoutePolyline"
            :route-info="activeRouteInfo"
            @select-marker="handleMarkerSelect"
            @retry-route="retryActiveRoute"
          />
        </div>
        <details v-if="selectedTripDetail" class="rounded-lg border border-slate-200 p-3 text-sm">
          <summary class="cursor-pointer font-medium text-slate-800">Detail perjalanan · {{ selectedTripDetail.name }}</summary>
          <div class="mt-3 space-y-3">
            <p class="text-slate-600">Jadwal: {{ selectedTripDetail.departure_time || '-' }} · Berangkat aktual: {{ selectedTripDetail.custom_actual_departure || 'Belum tercatat' }}</p>
            <a :href="`/app/delivery-trip/${selectedTripDetail.name}`" target="_blank" rel="noopener" class="text-sky-700 underline">Lihat dokumen perjalanan</a>
            <article v-for="stop in selectedTripDetail.delivery_stops" :key="stop.idx" class="border-t border-slate-100 pt-2">
              <div class="font-medium">{{ stop.idx }}. {{ stop.customer }} · {{ stop.delivery_note }}</div>
              <p class="text-slate-600">{{ stop.confirmation_text }}<span v-if="!stop.has_coordinates"> · Koordinat belum diatur</span></p>
              <p v-if="stop.details" class="text-slate-600">Catatan: {{ stop.details }}</p>
            </article>
          </div>
        </details>
      </div>

      <!-- Primary route selection, before the map on small screens -->
      <div class="order-1 lg:order-2 min-w-0 bg-white rounded-xl p-4 border border-slate-200 flex flex-col shadow-xs">
        <h3 class="font-semibold text-sm text-slate-900">Pilih perjalanan</h3>
        <p class="text-xs text-slate-500 mt-1 mb-3">Pilih trip untuk melihat rute rencana, bukan posisi GPS kendaraan.</p>
        <div class="overflow-y-auto space-y-2 max-h-64 lg:max-h-[420px]">
          <p v-if="loading && !tripsList.length" role="status" class="py-6 text-sm text-slate-500">Memuat perjalanan...</p>
          <p v-else-if="!tripsList.length" class="py-6 text-sm text-slate-500">Tidak ada perjalanan sesuai filter.</p>
          <button v-for="trip in tripsList" :key="trip.name" @click="handleSelectTripRow(trip)"
            :aria-pressed="selectedTripDetail?.name === trip.name"
            :class="['w-full text-left rounded-lg border p-3 transition focus-visible:outline-sky-600', selectedTripDetail?.name === trip.name ? 'border-sky-500 bg-sky-50' : 'border-slate-200 hover:bg-slate-50']">
            <div class="flex flex-wrap justify-between gap-2 text-sm font-semibold text-slate-900">
              <span>{{ trip.driver_name || trip.driver || trip.name }}</span><span>{{ trip.vehicle }}</span>
            </div>
            <div class="text-xs text-slate-500 mt-1">{{ trip.name }} · {{ trip.company }}</div>
            <div class="flex flex-wrap justify-between gap-2 mt-2 text-xs">
              <span :class="['rounded border px-2 py-0.5', getMonitoringBadgeClass(trip.monitoring_status)]">{{ trip.monitoring_status }}</span>
              <span>{{ trip.completed_stops }}/{{ trip.total_stops }} dikunjungi</span>
            </div>
            <div class="text-xs text-slate-600 mt-2">Konfirmasi terakhir: {{ trip.last_checkpoint?.text || 'Belum tersedia' }}</div>
            <div class="mt-2 text-xs font-medium text-sky-700">{{ selectedTripDetail?.name === trip.name ? 'Rute sedang ditampilkan' : 'Lihat rute' }}</div>
          </button>
        </div>

        <!-- Quick Action Footer -->
        <div class="border-t border-slate-100 pt-3 mt-3 grid grid-cols-2 gap-2">
          <button
            @click="$emit('nav', 'notes')"
            class="w-full py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-medium transition flex items-center justify-center space-x-1.5"
          >
            <span>Pesanan</span>
            <ArrowRight :size="13" />
          </button>
          <button
            @click="$emit('nav', 'trips')"
            class="w-full py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-xs font-medium transition flex items-center justify-center space-x-1.5"
          >
            <span>Perjalanan</span>
            <ArrowRight :size="13" />
          </button>
        </div>
      </div>
    </div>
    <section class="order-last rounded-xl border border-slate-200 bg-white p-5">
      <h3 class="text-sm font-semibold text-slate-900 mb-3">Aktivitas terkini</h3>
      <div class="grid sm:grid-cols-2 gap-3">
        <article v-for="(act, idx) in activityLog" :key="idx" class="rounded-lg border border-slate-100 p-3 text-sm">
          <div class="font-medium text-slate-800">{{ act.title }}</div>
          <p class="text-slate-600 mt-1">{{ act.description }}</p>
          <span class="text-xs text-slate-500">{{ act.time }} · {{ act.status }}</span>
        </article>
      </div>
      <p v-if="!activityLog.length" class="text-sm text-slate-500">Belum ada aktivitas tercatat.</p>
    </section>

    <!-- Main Monitoring Table: Trip, Company, Driver, Plat Nomor, Jadwal, Berangkat Aktual, Progres, Checkpoint Terakhir, Status -->
    <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
      <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div>
          <h3 class="font-semibold text-sm text-slate-900">Monitoring Perjalanan Armada Internal</h3>
          <p class="text-xs text-slate-400">Pilih baris trip untuk memvisualisasikan rute rencana OSRM pada peta di atas</p>
        </div>

      </div>

      <!-- Table Body -->
      <div class="overflow-x-auto rounded-lg border border-slate-200">
        <table class="w-full text-left text-sm text-slate-600">
          <thead class="bg-slate-50 text-[10px] uppercase font-semibold text-slate-500 border-b border-slate-200">
            <tr>
              <th class="px-4 py-3">Trip & Company</th>
              <th class="px-4 py-3">Driver & Armada</th>
              <th class="px-4 py-3">Jadwal Berangkat</th>
              <th class="px-4 py-3">Berangkat Aktual</th>
              <th class="px-4 py-3">Progres Kunjungan</th>
              <th class="px-4 py-3">Checkpoint Terakhir</th>
              <th class="px-4 py-3">Status</th>
              <th class="px-4 py-3 text-right">Aksi</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr
              v-for="trip in tripsList"
              :key="trip.name"
              @click="handleSelectTripRow(trip)"
              :class="[
                'cursor-pointer transition',
                selectedTripDetail?.name === trip.name ? 'bg-sky-50/80 font-medium' : 'hover:bg-slate-50/70'
              ]"
            >
              <td class="px-4 py-3">
                <div class="font-semibold text-slate-900">{{ trip.name }}</div>
                <div class="text-[11px] text-slate-400 mt-0.5">{{ trip.company || '-' }}</div>
              </td>
              <td class="px-4 py-3">
                <div class="font-medium text-slate-800">{{ trip.driver_name || trip.driver }}</div>
                <div class="text-[11px] text-slate-400 mt-0.5">{{ trip.vehicle }}</div>
              </td>
              <td class="px-4 py-3 text-[11px]">
                {{ trip.departure_time ? trip.departure_time.slice(0, 16) : '-' }}
              </td>
              <td class="px-4 py-3 text-[11px]">
                <span :class="trip.custom_actual_departure ? 'text-slate-800 font-medium' : 'text-amber-600'">
                  {{ trip.custom_actual_departure ? trip.custom_actual_departure.slice(0, 16) : 'Belum Berangkat' }}
                </span>
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center space-x-2">
                  <div class="w-16 bg-slate-200 rounded-full h-1.5 overflow-hidden">
                    <div
                      class="bg-sky-500 h-1.5 rounded-full"
                      :style="{ width: `${(trip.completed_stops / Math.max(1, trip.total_stops)) * 100}%` }"
                    ></div>
                  </div>
                  <span class="text-[11px] font-semibold text-slate-700">
                    {{ trip.completed_stops }}/{{ trip.total_stops }}
                  </span>
                </div>
              </td>
              <td class="px-4 py-3 text-[11px] max-w-[160px] truncate" :title="trip.last_checkpoint?.text">
                {{ trip.last_checkpoint?.text || '-' }}
              </td>
              <td class="px-4 py-3">
                <span
                  :class="[
                    'px-2 py-0.5 rounded text-[10px] font-semibold border uppercase',
                    getMonitoringBadgeClass(trip.monitoring_status || trip.status)
                  ]"
                >
                  {{ trip.monitoring_status || trip.status }}
                </span>
              </td>
              <td class="px-4 py-3 text-right">
                <div class="inline-flex items-center space-x-1.5" @click.stop>
                  <button
                    v-if="trip.docstatus === 1 && !trip.custom_actual_departure && trip.status !== 'Completed'"
                    @click="confirmDeparture(trip.name)"
                    class="px-2 py-1 bg-sky-600 hover:bg-sky-700 text-white rounded text-[10px] font-medium transition"
                  >
                    Berangkat
                  </button>
                  <button
                    @click="handleSelectTripRow(trip)"
                    :class="[
                      'px-2 py-1 rounded text-[10px] font-medium border transition',
                      selectedTripDetail?.name === trip.name ? 'bg-sky-600 text-white border-sky-600' : 'border-slate-200 hover:bg-slate-100 text-slate-700'
                    ]"
                  >
                    {{ selectedTripDetail?.name === trip.name ? 'Aktif' : 'Lihat Rute' }}
                  </button>
                </div>
              </td>
            </tr>

            <tr v-if="tripsList.length === 0">
              <td colspan="8" class="px-4 py-8 text-center text-slate-400 text-xs">
                Tidak ada data perjalanan armada ditemukan.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="flex items-center justify-end gap-3 text-sm">
        <button :disabled="tablePage === 1" @click="tablePage--; loadTripsTable()" class="disabled:opacity-40">Sebelumnya</button>
        <span>{{ tablePage }} / {{ Math.max(1, Math.ceil(tableTotal / 15)) }}</span>
        <button :disabled="tablePage * 15 >= tableTotal" @click="tablePage++; loadTripsTable()" class="disabled:opacity-40">Berikutnya</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  Package,
  Truck,
  CheckCircle2,
  Check,
  MapPin,
  RefreshCw,
  ArrowRight,
  Calendar
} from 'lucide-vue-next'
import OperationsMap from '@/components/OperationsMap.vue'
import { DeliveryApi } from '@/api'
import { useVisibleRefresh } from '@/composables/useVisibleRefresh'

const emit = defineEmits(['nav', 'open-note'])

const loading = ref(false)
const kpi = ref({})
const mapMarkers = ref([])
const unlocatedCount = ref(0)
const activityLog = ref([])

// Table trips state
const tripsList = ref([])
const tableStatusFilter = ref('All')
const tableSearch = ref('')
const selectedTripDetail = ref(null)
const companies = ref([])
const companyFilter = ref('')
const error = ref('')
const routeError = ref('')
const loadingTrip = ref(false)
const updatedAt = ref('')
const tablePage = ref(1)
const tableTotal = ref(0)
let selectionVersion = 0
let tableVersion = 0
let refreshQueued = false

function applyFilters() {
  tablePage.value = 1
  loadTripsTable()
}

function changeCompany() {
  tablePage.value = 1
  clearSelectedTrip()
  refreshDashboard()
}

function getMonitoringBadgeClass(status) {
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

const activeMapMarkers = computed(() => {
  if (!selectedTripDetail.value) {
    return mapMarkers.value
  }

  // Build focused markers for selected trip
  const list = []
  if (selectedTripDetail.value.has_origin_coordinates) {
    list.push({
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

  ;(selectedTripDetail.value.delivery_stops || []).forEach((stop) => {
    if (stop.has_coordinates) {
      list.push({
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

  return list
})

const activeRoutePolyline = computed(() => {
  return selectedTripDetail.value?.route?.route_points || []
})

const activeRouteInfo = computed(() => {
  return selectedTripDetail.value?.route || null
})

async function refreshDashboard() {
  if (loading.value) { refreshQueued = true; return }
  loading.value = true
  error.value = ''
  try {
    const res = await DeliveryApi.getSummary({ company_filter: companyFilter.value || null })
    kpi.value = res.kpi || {}
    mapMarkers.value = res.map_markers || []
    unlocatedCount.value = res.unlocated_count || 0
    activityLog.value = res.activity_log || []
    await loadTripsTable()
    if (selectedTripDetail.value) {
      const name = selectedTripDetail.value.name
      const version = selectionVersion
      const detail = await DeliveryApi.getTripDetail(name, false)
      if (version === selectionVersion && selectedTripDetail.value?.name === name) {
        selectedTripDetail.value = { ...detail, route: selectedTripDetail.value.route }
      }
    }
    updatedAt.value = new Date().toLocaleTimeString('id-ID')
  } catch (err) {
    error.value = err.message || 'Gagal memperbarui dashboard. Data sebelumnya tetap ditampilkan.'
  } finally {
    loading.value = false
    if (refreshQueued) { refreshQueued = false; refreshDashboard() }
  }
}

async function loadTripsTable() {
  const version = ++tableVersion
  try {
    const res = await DeliveryApi.getTrips({
      status_filter: tableStatusFilter.value === 'All' ? null : tableStatusFilter.value,
      search: tableSearch.value,
      company_filter: companyFilter.value || null,
      page: tablePage.value,
      page_size: 15
    })
    if (version !== tableVersion) return
    tripsList.value = res.items || []
    tableTotal.value = res.total_count || 0
    if (selectedTripDetail.value && !tripsList.value.some(t => t.name === selectedTripDetail.value.name)) clearSelectedTrip()
  } catch (err) {
    if (version === tableVersion) error.value = err.message || 'Gagal memuat perjalanan.'
  }
}

async function handleSelectTripRow(trip) {
  if (selectedTripDetail.value?.name === trip.name) {
    return
  }
  const version = ++selectionVersion
  loadingTrip.value = true
  routeError.value = ''
  try {
    const detail = await DeliveryApi.getTripDetail(trip.name)
    if (version === selectionVersion) selectedTripDetail.value = detail
  } catch (err) {
    if (version === selectionVersion) routeError.value = 'Gagal memuat rute trip: ' + err.message
  } finally {
    if (version === selectionVersion) loadingTrip.value = false
  }
}

function clearSelectedTrip() {
  selectionVersion++
  loadingTrip.value = false
  routeError.value = ''
  selectedTripDetail.value = null
}

async function retryActiveRoute() {
  if (!selectedTripDetail.value) return
  const name = selectedTripDetail.value.name
  const version = selectionVersion
  try {
    const res = await DeliveryApi.getTripRoute(name)
    if (version === selectionVersion && selectedTripDetail.value?.name === name) selectedTripDetail.value.route = res
  } catch (err) {
    alert('Gagal memuat rute jalan: ' + err.message)
  }
}

async function confirmDeparture(name) {
  if (!confirm(`Konfirmasi keberangkatan untuk trip ${name}? Waktu keberangkatan server akan dicatat.`)) return
  try {
    await DeliveryApi.markTripDeparted(name)
    await refreshDashboard()
  } catch (err) {
    alert(err.message || 'Gagal mengonfirmasi keberangkatan')
  }
}

function handleMarkerSelect(marker) {
  if (marker.type === 'origin') return
  emit('open-note', marker.id)
}

useVisibleRefresh(refreshDashboard)
onMounted(() => {
  refreshDashboard()
  DeliveryApi.getFleetResources().then(res => { companies.value = res.companies || [] }).catch(err => { error.value = err.message })
})
</script>
