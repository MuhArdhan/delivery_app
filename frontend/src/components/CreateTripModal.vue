<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 overflow-y-auto bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4">
    <div class="relative bg-white rounded-xl shadow-xl max-w-2xl w-full border border-slate-200 overflow-hidden transform transition-all">
      <!-- Header -->
      <div class="bg-slate-900 text-white px-6 py-4 flex items-center justify-between border-b border-slate-800">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-200">
            <Route :size="15" class="text-sky-400" />
          </div>
          <div>
            <h3 class="font-semibold text-sm text-white">Buat Delivery Trip (Armada Sendiri)</h3>
            <p class="text-xs text-slate-400">Rute Multi-Drop & Penugasan Pengemudi</p>
          </div>
        </div>
        <button @click="close" class="text-slate-400 hover:text-white p-1 rounded-lg transition">
          <X :size="16" />
        </button>
      </div>

      <!-- Body -->
      <div class="p-6 space-y-5 max-h-[80vh] overflow-y-auto text-xs">
        <!-- Driver & Vehicle Selector -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
        </div>

        <div>
          <label class="block text-[10px] font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
            Waktu Keberangkatan
          </label>
          <input
            v-model="form.departure_time"
            type="datetime-local"
            class="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400 bg-white text-slate-700"
          />
        </div>

        <!-- Sequenced Stops Section -->
        <div>
          <div class="flex justify-between items-center mb-2">
            <label class="block text-[10px] font-semibold text-slate-700 uppercase tracking-wider">
              Urutan Titik Singgah / Waypoints ({{ stopList.length }} Stops)
            </label>
            <span class="text-[11px] text-slate-500">Urutkan titik pengantaran</span>
          </div>

          <div v-if="stopList.length === 0" class="text-center py-8 border border-dashed border-slate-200 rounded-lg text-slate-400 text-xs">
            Belum ada Delivery Note yang dipilih.
          </div>

          <div v-else class="space-y-2">
            <div
              v-for="(stop, idx) in stopList"
              :key="stop.delivery_note"
              class="flex items-center justify-between p-3 rounded-lg border border-slate-200 bg-slate-50/70 hover:bg-slate-50 transition"
            >
              <div class="flex items-center space-x-3 min-w-0">
                <span class="w-5 h-5 rounded-md bg-slate-800 text-white font-medium text-[10px] flex items-center justify-center flex-shrink-0">
                  {{ idx + 1 }}
                </span>
                <div class="min-w-0">
                  <div class="text-xs font-semibold text-slate-800 truncate">
                    {{ stop.customer || 'Pelanggan' }}
                    <span class="font-normal text-slate-500 text-[11px]">({{ stop.delivery_note }})</span>
                  </div>
                  <div class="text-[11px] text-slate-500 truncate max-w-md">
                    {{ stop.customer_address || stop.address_display || '-' }}
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
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { Route, X, ChevronUp, ChevronDown } from 'lucide-vue-next'
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

const form = reactive({
  driver: '',
  vehicle: '',
  departure_time: new Date().toISOString().slice(0, 16),
})

function moveStop(index, delta) {
  const newIndex = index + delta
  if (newIndex < 0 || newIndex >= stopList.value.length) return
  const item = stopList.value.splice(index, 1)[0]
  stopList.value.splice(newIndex, 0, item)
}

function removeStop(index) {
  stopList.value.splice(index, 1)
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

watch(() => props.isOpen, (open) => {
  if (open) {
    stopList.value = [...(props.initialNotes || [])]
    if (props.drivers && props.drivers.length > 0 && !form.driver) {
      form.driver = props.drivers[0].name
    }
    if (props.vehicles && props.vehicles.length > 0 && !form.vehicle) {
      form.vehicle = props.vehicles[0].name
    }
  }
})
</script>