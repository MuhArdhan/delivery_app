<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 overflow-y-auto bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4">
    <div class="relative bg-white rounded-xl shadow-xl max-w-3xl w-full border border-slate-200 overflow-hidden transform transition-all">
      <!-- Header -->
      <div class="bg-slate-900 text-white px-6 py-4 flex items-center justify-between border-b border-slate-800">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-200">
            <Route :size="15" class="text-sky-400" />
          </div>
          <div>
            <h3 class="font-semibold text-sm text-white">Buat Delivery Trip</h3>
            <p class="text-xs text-slate-400">Rute Multi-Drop & Penugasan Pengemudi</p>
          </div>
        </div>
        <button @click="close" class="text-slate-400 hover:text-white p-1 rounded-lg transition">
          <X :size="16" />
        </button>
      </div>

      <!-- Body -->
      <div class="p-6 space-y-5 max-h-[80vh] overflow-y-auto text-xs">
        <!-- Company & Origin Coordinates Alert -->
        <div v-if="detectedCompany" class="p-3.5 rounded-lg border bg-slate-50 flex items-center justify-between border-slate-200">
          <div>
            <span class="text-[10px] uppercase font-semibold text-slate-500 tracking-wider block">Company Asal Keberangkatan</span>
            <div class="text-xs font-semibold text-slate-800 mt-0.5">{{ detectedCompany }}</div>
            <div class="text-[11px] mt-0.5 flex items-center space-x-1.5">
              <span v-if="originHasLocation" class="text-emerald-700 font-medium">
                Koordinat Asal: {{ originLat }}, {{ originLng }}
              </span>
              <span v-else class="text-amber-700 font-medium">
                Koordinat asal gudang belum diatur.
              </span>
            </div>
          </div>
          <button
            type="button"
            @click="openCompanyLocationModal"
            class="px-2.5 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-medium transition"
          >
            {{ originHasLocation ? 'Ubah Koordinat Asal' : 'Atur Lokasi Asal' }}
          </button>
        </div>

        <!-- Driver & Vehicle & Departure Time Selector -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label class="block text-[10px] font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              Pilih Driver *
            </label>
            <select
              v-model="form.driver"
              required
              class="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400 bg-white text-slate-700"
            >
              <option value="" disabled>-- Pilih Driver --</option>
              <option v-for="d in drivers" :key="d.name" :value="d.name">
                {{ d.full_name }} {{ d.cell_number ? `(${d.cell_number})` : '' }}
              </option>
            </select>
          </div>

          <div>
            <label class="block text-[10px] font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              Pilih Kendaraan *
            </label>
            <select
              v-model="form.vehicle"
              required
              class="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400 bg-white text-slate-700"
            >
              <option value="" disabled>-- Pilih Kendaraan --</option>
              <option v-for="v in vehicles" :key="v.name" :value="v.name">
                {{ v.license_plate }} - {{ v.make }} {{ v.model }}
              </option>
            </select>
          </div>

          <div>
            <label class="block text-[10px] font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              Usulan Waktu Berangkat
            </label>
            <input
              v-model="form.departure_time"
              type="datetime-local"
              class="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400 bg-white text-slate-700"
            />
          </div>
        </div>

        <!-- Sequenced Stops Section -->
        <div>
          <div class="flex justify-between items-center mb-2">
            <div>
              <label class="block text-[10px] font-semibold text-slate-700 uppercase tracking-wider">
                Urutan Titik Singgah / Waypoints ({{ stopList.length }} Stops)
              </label>
              <span class="text-[11px] text-slate-500">Urutkan titik pengantaran dari pertama hingga terakhir</span>
            </div>

            <button
              type="button"
              @click="isAddStopOpen = !isAddStopOpen"
              class="px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium transition flex items-center space-x-1"
            >
              <Plus :size="12" />
              <span>Tambah Stop Dari Antrean</span>
            </button>
          </div>

          <!-- Add Stop Drawer / Selector -->
          <div v-if="isAddStopOpen" class="p-3 mb-3 border border-slate-200 rounded-lg bg-slate-50/90 space-y-2">
            <div class="flex justify-between items-center">
              <span class="font-semibold text-xs text-slate-800">Pilih Delivery Note Tersedia</span>
              <button type="button" @click="isAddStopOpen = false" class="text-slate-400 hover:text-slate-600">
                <X :size="14" />
              </button>
            </div>
            <div v-if="loadingEligible" class="text-xs text-slate-500 py-3 text-center">
              Memuat Delivery Note tersedia...
            </div>
            <div v-else-if="availableEligibleNotes.length === 0" class="text-xs text-slate-400 py-3 text-center">
              Tidak ada Delivery Note siap kirim lainnya untuk company ini.
            </div>
            <div v-else class="max-h-40 overflow-y-auto space-y-1.5 pr-1">
              <div
                v-for="note in availableEligibleNotes"
                :key="note.name"
                @click="addStopFromEligible(note)"
                class="p-2 bg-white rounded border border-slate-200 hover:border-sky-400 cursor-pointer transition flex items-center justify-between text-xs"
              >
                <div>
                  <span class="font-medium text-slate-900">{{ note.name }}</span>
                  <span class="text-slate-500 ml-1.5">({{ note.customer }})</span>
                  <div class="text-[11px] text-slate-400 truncate max-w-sm">{{ note.customer_address || '-' }}</div>
                </div>
                <div class="flex items-center space-x-2">
                  <span
                    :class="[
                      'px-1.5 py-0.5 rounded text-[10px] font-medium border',
                      note.has_coordinates ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-amber-50 text-amber-700 border-amber-200'
                    ]"
                  >
                    {{ note.has_coordinates ? 'Lokasi OK' : 'Lokasi Belum Ada' }}
                  </span>
                  <span class="text-sky-600 font-semibold text-[11px]">+ Tambah</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Stops List -->
          <div v-if="stopList.length === 0" class="text-center py-8 border border-dashed border-slate-200 rounded-lg text-slate-400 text-xs">
            Belum ada Delivery Note yang dipilih. Silakan tambah stop dari antrean di atas.
          </div>

          <div v-else class="space-y-2">
            <div
              v-for="(stop, idx) in stopList"
              :key="stop.delivery_note || stop.name"
              class="p-3 rounded-lg border border-slate-200 bg-slate-50/70 hover:bg-slate-50 transition flex items-start justify-between"
            >
              <div class="flex items-start space-x-3 min-w-0 flex-1">
                <span class="w-6 h-6 rounded-md bg-slate-800 text-white font-medium text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                  {{ idx + 1 }}
                </span>
                <div class="min-w-0 flex-1">
                  <div class="flex items-center space-x-2">
                    <span class="text-xs font-semibold text-slate-800 truncate">
                      {{ stop.customer || 'Pelanggan' }}
                    </span>
                    <span class="font-medium text-slate-500 text-[11px]">
                      ({{ stop.delivery_note || stop.name }})
                    </span>
                  </div>
                  <div class="text-[11px] text-slate-500 truncate mt-0.5 max-w-md">
                    {{ stop.customer_address || stop.address_display || '-' }}
                  </div>

                  <!-- Stop Coordinates Status -->
                  <div class="mt-2 flex items-center space-x-2">
                    <span
                      v-if="hasValidCoords(stop.lat, stop.lng)"
                      class="px-2 py-0.5 bg-emerald-50 border border-emerald-200 text-emerald-700 text-[10px] font-medium rounded inline-flex items-center space-x-1"
                    >
                      <Check :size="10" />
                      <span>Koordinat: {{ stop.lat }}, {{ stop.lng }}</span>
                    </span>
                    <button
                      v-else
                      type="button"
                      @click="openCustomerLocationModal(stop)"
                      class="px-2 py-0.5 bg-amber-50 hover:bg-amber-100 border border-amber-200 text-amber-800 text-[10px] font-medium rounded transition inline-flex items-center space-x-1"
                    >
                      <MapPin :size="10" />
                      <span>Atur Lokasi Customer</span>
                    </button>
                    <button
                      v-if="hasValidCoords(stop.lat, stop.lng)"
                      type="button"
                      @click="openCustomerLocationModal(stop)"
                      class="text-[10px] text-slate-500 hover:text-slate-800 underline transition"
                    >
                      Ubah
                    </button>
                  </div>
                </div>
              </div>

              <!-- Reorder buttons & Remove -->
              <div class="flex items-center space-x-1 flex-shrink-0 ml-3">
                <button
                  type="button"
                  @click="moveStop(idx, -1)"
                  :disabled="idx === 0"
                  class="p-1 rounded text-slate-400 hover:text-slate-700 disabled:opacity-20 transition"
                  title="Naikkan Urutan"
                >
                  <ChevronUp :size="14" />
                </button>
                <button
                  type="button"
                  @click="moveStop(idx, 1)"
                  :disabled="idx === stopList.length - 1"
                  class="p-1 rounded text-slate-400 hover:text-slate-700 disabled:opacity-20 transition"
                  title="Turunkan Urutan"
                >
                  <ChevronDown :size="14" />
                </button>
                <button
                  type="button"
                  @click="removeStop(idx)"
                  class="p-1 text-slate-400 hover:text-rose-500 rounded transition ml-1"
                  title="Hapus Stop"
                >
                  <X :size="14" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="bg-slate-50 px-6 py-4 border-t border-slate-200 flex items-center justify-between">
        <div class="text-xs text-slate-500">
          Total: <strong class="text-slate-800">{{ stopList.length }} Pengiriman</strong>
        </div>
        <div class="flex items-center space-x-2">
          <button
            type="button"
            @click="close"
            class="px-3.5 py-2 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-200 transition"
          >
            Batal
          </button>
          <button
            type="button"
            @click="submitTrip"
            :disabled="submitting || !form.driver || !form.vehicle || stopList.length === 0"
            class="px-4 py-2 rounded-lg text-xs font-medium bg-sky-600 hover:bg-sky-700 text-white transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1.5"
          >
            <span v-if="submitting">Membuat Trip...</span>
            <span v-else>Jadwalkan Delivery Trip</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Submodal: Set Customer Location -->
    <div v-if="isCustomerModalOpen" class="fixed inset-0 z-60 bg-slate-950/70 flex items-center justify-center p-4">
      <div class="bg-white rounded-xl shadow-xl max-w-md w-full border border-slate-200 overflow-hidden">
        <div class="bg-slate-900 text-white px-5 py-3.5 flex items-center justify-between border-b border-slate-800">
          <h4 class="font-semibold text-xs text-white">Atur Lokasi Pelanggan</h4>
          <button @click="isCustomerModalOpen = false" class="text-slate-400 hover:text-white p-1">
            <X :size="14" />
          </button>
        </div>
        <div class="p-5 space-y-4 text-xs">
          <div>
            <span class="text-slate-400 block text-[11px]">Pelanggan:</span>
            <span class="font-semibold text-slate-800 text-sm">{{ activeCustomerStop?.customer }}</span>
          </div>
          <div>
            <span class="text-slate-400 block text-[11px]">Panduan Alamat:</span>
            <p class="text-slate-600 bg-slate-50 p-2.5 rounded border border-slate-200 text-[11px] leading-relaxed">
              {{ activeCustomerStop?.customer_address || activeCustomerStop?.address_display || '-' }}
            </p>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Latitude *
              </label>
              <input
                v-model.number="customerCoordForm.lat"
                type="number"
                step="any"
                placeholder="-7.6147"
                class="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400"
              />
            </div>
            <div>
              <label class="block text-[10px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Longitude *
              </label>
              <input
                v-model.number="customerCoordForm.lng"
                type="number"
                step="any"
                placeholder="110.6869"
                class="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400"
              />
            </div>
          </div>
        </div>
        <div class="bg-slate-50 px-5 py-3 border-t border-slate-200 flex justify-end space-x-2">
          <button
            type="button"
            @click="isCustomerModalOpen = false"
            class="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-200 transition"
          >
            Batal
          </button>
          <button
            type="button"
            @click="saveCustomerLocation"
            :disabled="savingLocation || customerCoordForm.lat === null || customerCoordForm.lng === null"
            class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-sky-600 hover:bg-sky-700 text-white transition disabled:opacity-50"
          >
            Simpan Lokasi
          </button>
        </div>
      </div>
    </div>

    <!-- Submodal: Set Company Origin Location -->
    <div v-if="isCompanyModalOpen" class="fixed inset-0 z-60 bg-slate-950/70 flex items-center justify-center p-4">
      <div class="bg-white rounded-xl shadow-xl max-w-md w-full border border-slate-200 overflow-hidden">
        <div class="bg-slate-900 text-white px-5 py-3.5 flex items-center justify-between border-b border-slate-800">
          <h4 class="font-semibold text-xs text-white">Atur Lokasi Keberangkatan Gudang</h4>
          <button @click="isCompanyModalOpen = false" class="text-slate-400 hover:text-white p-1">
            <X :size="14" />
          </button>
        </div>
        <div class="p-5 space-y-4 text-xs">
          <div>
            <span class="text-slate-400 block text-[11px]">Company / Gudang Asal:</span>
            <span class="font-semibold text-slate-800 text-sm">{{ detectedCompany }}</span>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[10px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Latitude *
              </label>
              <input
                v-model.number="companyCoordForm.lat"
                type="number"
                step="any"
                placeholder="-7.6147"
                class="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400"
              />
            </div>
            <div>
              <label class="block text-[10px] font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Longitude *
              </label>
              <input
                v-model.number="companyCoordForm.lng"
                type="number"
                step="any"
                placeholder="110.6869"
                class="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400"
              />
            </div>
          </div>
        </div>
        <div class="bg-slate-50 px-5 py-3 border-t border-slate-200 flex justify-end space-x-2">
          <button
            type="button"
            @click="isCompanyModalOpen = false"
            class="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-200 transition"
          >
            Batal
          </button>
          <button
            type="button"
            @click="saveCompanyLocation"
            :disabled="savingLocation || companyCoordForm.lat === null || companyCoordForm.lng === null"
            class="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-sky-600 hover:bg-sky-700 text-white transition disabled:opacity-50"
          >
            Simpan Lokasi Asal
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue'
import { Route, X, ChevronUp, ChevronDown, Plus, Check, MapPin } from 'lucide-vue-next'
import { DeliveryApi } from '@/api'

const props = defineProps({
  isOpen: Boolean,
  initialNotes: {
    type: Array,
    default: () => []
  },
  drivers: {
    type: Array,
    default: () => []
  },
  vehicles: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close', 'created'])

const submitting = ref(false)
const stopList = ref([])
const eligibleNotes = ref([])
const loadingEligible = ref(false)
const isAddStopOpen = ref(false)

const originLat = ref(null)
const originLng = ref(null)
const originHasLocation = ref(false)

// Location modals
const isCustomerModalOpen = ref(false)
const activeCustomerStop = ref(null)
const customerCoordForm = reactive({ lat: null, lng: null })

const isCompanyModalOpen = ref(false)
const companyCoordForm = reactive({ lat: null, lng: null })
const savingLocation = ref(false)

const form = reactive({
  driver: '',
  vehicle: '',
  departure_time: new Date().toISOString().slice(0, 16),
})

const detectedCompany = computed(() => {
  for (const s of stopList.value) {
    if (s.company) return s.company
  }
  return ''
})

const availableEligibleNotes = computed(() => {
  const currentDns = new Set(stopList.value.map(s => s.name || s.delivery_note))
  return eligibleNotes.value.filter(n => !currentDns.has(n.name))
})

function hasValidCoords(lat, lng) {
  if (lat === null || lat === undefined || lng === null || lng === undefined) return false
  const nLat = Number(lat)
  const nLng = Number(lng)
  return !isNaN(nLat) && !isNaN(nLng) && (nLat !== 0 || nLng !== 0)
}

async function loadCompanyCoordinates(company) {
  if (!company) return
  try {
    const res = await DeliveryApi.getCompanyDispatchLocation(company)
    originLat.value = res.latitude
    originLng.value = res.longitude
    originHasLocation.value = res.has_location
  } catch (err) {
    console.warn('Gagal memuat koordinat company:', err)
  }
}

async function loadEligibleNotes() {
  loadingEligible.value = true
  try {
    const res = await DeliveryApi.getEligibleDeliveryNotes(detectedCompany.value || null)
    eligibleNotes.value = res || []
  } catch (err) {
    console.warn('Gagal memuat eligible notes:', err)
  } finally {
    loadingEligible.value = false
  }
}

function addStopFromEligible(note) {
  stopList.value.push({
    delivery_note: note.name,
    customer: note.customer,
    address: note.shipping_address_name,
    customer_address: note.customer_address,
    company: note.company,
    lat: note.lat,
    lng: note.lng
  })

  if (note.company && !originHasLocation.value) {
    loadCompanyCoordinates(note.company)
  }
}

function moveStop(index, delta) {
  const newIndex = index + delta
  if (newIndex < 0 || newIndex >= stopList.value.length) return
  const item = stopList.value.splice(index, 1)[0]
  stopList.value.splice(newIndex, 0, item)
}

function removeStop(index) {
  stopList.value.splice(index, 1)
}

function openCustomerLocationModal(stop) {
  activeCustomerStop.value = stop
  customerCoordForm.lat = stop.lat !== undefined ? stop.lat : null
  customerCoordForm.lng = stop.lng !== undefined ? stop.lng : null
  isCustomerModalOpen.value = true
}

async function saveCustomerLocation() {
  if (!activeCustomerStop.value) return
  savingLocation.value = true
  try {
    const cust = activeCustomerStop.value.customer
    const res = await DeliveryApi.setCustomerLocation(cust, customerCoordForm.lat, customerCoordForm.lng)
    activeCustomerStop.value.lat = res.latitude
    activeCustomerStop.value.lng = res.longitude

    // Also update any other stop in stopList for the same customer
    for (const s of stopList.value) {
      if (s.customer === cust) {
        s.lat = res.latitude
        s.lng = res.longitude
      }
    }
    isCustomerModalOpen.value = false
  } catch (err) {
    alert(err.message || 'Gagal menyimpan lokasi customer')
  } finally {
    savingLocation.value = false
  }
}

function openCompanyLocationModal() {
  companyCoordForm.lat = originLat.value
  companyCoordForm.lng = originLng.value
  isCompanyModalOpen.value = true
}

async function saveCompanyLocation() {
  if (!detectedCompany.value) return
  savingLocation.value = true
  try {
    const res = await DeliveryApi.setCompanyDispatchLocation(detectedCompany.value, companyCoordForm.lat, companyCoordForm.lng)
    originLat.value = res.latitude
    originLng.value = res.longitude
    originHasLocation.value = res.has_location
    isCompanyModalOpen.value = false
  } catch (err) {
    alert(err.message || 'Gagal menyimpan lokasi company')
  } finally {
    savingLocation.value = false
  }
}

async function submitTrip() {
  if (!form.driver || !form.vehicle || stopList.value.length === 0) return
  submitting.value = true
  try {
    const formattedStops = stopList.value.map(s => ({
      delivery_note: s.name || s.delivery_note,
      customer: s.customer,
      address: s.shipping_address_name || s.address,
      customer_address: s.address_display || s.customer_address || s.shipping_address,
      lat: s.lat,
      lng: s.lng,
      details: s.details || ''
    }))

    const res = await DeliveryApi.createTrip({
      driver: form.driver,
      vehicle: form.vehicle,
      departure_time: form.departure_time,
      company: detectedCompany.value || null,
      stops: formattedStops
    })

    // Also submit trip into Scheduled status
    if (res.trip_name) {
      try {
        await DeliveryApi.submitTrip(res.trip_name)
      } catch (e) {
        console.warn('Trip created in Draft status:', e)
      }
    }

    emit('created', res)
    close()
  } catch (err) {
    alert(err.message || 'Gagal membuat delivery trip')
  } finally {
    submitting.value = false
  }
}

function close() {
  emit('close')
}

watch(() => props.isOpen, async (open) => {
  if (open) {
    stopList.value = [...(props.initialNotes || [])]
    if (props.drivers && props.drivers.length > 0 && !form.driver) {
      form.driver = props.drivers[0].name
    }
    if (props.vehicles && props.vehicles.length > 0 && !form.vehicle) {
      form.vehicle = props.vehicles[0].name
    }
    if (detectedCompany.value) {
      await loadCompanyCoordinates(detectedCompany.value)
    }
    await loadEligibleNotes()
  }
})
</script>
