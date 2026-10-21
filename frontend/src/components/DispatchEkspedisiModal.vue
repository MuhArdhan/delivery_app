<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 overflow-y-auto bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4">
    <div class="relative bg-white rounded-xl shadow-xl max-w-xl w-full border border-slate-200 overflow-hidden transform transition-all">
      <!-- Header -->
      <div class="bg-slate-900 text-white px-6 py-4 flex items-center justify-between border-b border-slate-800">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-200">
            <Send :size="15" class="text-sky-400" />
          </div>
          <div>
            <h3 class="font-semibold text-sm text-white">Kirim via Ekspedisi (3PL)</h3>
            <p class="text-xs text-slate-400">Integrasi Biteship & Manajemen Resi Eksternal</p>
          </div>
        </div>
        <button @click="close" class="text-slate-400 hover:text-white p-1 rounded-lg transition">
          <X :size="16" />
        </button>
      </div>

      <!-- Body -->
      <div class="p-6 space-y-5 max-h-[80vh] overflow-y-auto text-xs">
        <!-- Delivery Note Summary Card -->
        <div class="bg-slate-50 border border-slate-200 rounded-lg p-4 flex justify-between items-start">
          <div>
            <span class="text-slate-400 font-medium">Dokumen:</span>
            <span class="ml-1 font-semibold text-slate-800">{{ note?.name }}</span>
            <div class="mt-1 font-semibold text-slate-700">{{ note?.customer }}</div>
            <div class="mt-0.5 text-slate-500 line-clamp-2 max-w-sm">{{ note?.address_display || note?.shipping_address }}</div>
          </div>
          <div class="text-right">
            <span class="inline-block px-2.5 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
              {{ note?.items?.length || 1 }} Produk
            </span>
          </div>
        </div>

        <!-- Courier Selector -->
        <div>
          <label class="block text-[10px] font-semibold text-slate-700 uppercase tracking-wider mb-2">
            Pilih Kurir Ekspedisi *
          </label>
          <div class="grid grid-cols-3 sm:grid-cols-4 gap-2">
            <button
              v-for="c in couriers"
              :key="c.code"
              type="button"
              @click="selectCourier(c)"
              :class="[
                'p-2.5 rounded-lg border text-center transition flex flex-col items-center justify-center space-y-1',
                form.courier_code === c.code 
                  ? 'border-sky-500 bg-sky-50 text-sky-900 font-semibold' 
                  : 'border-slate-200 hover:border-slate-300 bg-white text-slate-700'
              ]"
            >
              <span class="text-xs font-semibold tracking-tight uppercase">{{ c.code }}</span>
              <span class="text-[10px] text-slate-500 line-clamp-1">{{ c.name.replace('Express', '') }}</span>
            </button>
          </div>
        </div>

        <!-- Service & Weight -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-[10px] font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              Layanan Kurir
            </label>
            <select
              v-model="form.courier_service"
              class="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400 bg-white text-slate-700"
            >
              <option value="REG">Reguler (2-3 Hari)</option>
              <option value="EXPRESS">Express / Next Day (1 Hari)</option>
              <option value="CARGO">Cargo / Trucking (Hemat)</option>
              <option value="INSTANT">Instant Delivery</option>
            </select>
          </div>

          <div>
            <label class="block text-[10px] font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
              Berat Paket (Gram)
            </label>
            <div class="relative">
              <input
                v-model.number="form.weight_grams"
                type="number"
                min="100"
                step="100"
                class="w-full text-xs px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400 text-slate-800"
                placeholder="1000"
              />
              <span class="absolute right-3 top-2 text-xs text-slate-400">gr</span>
            </div>
          </div>
        </div>

        <!-- Estimasi Ongkir Checker -->
        <div class="bg-slate-50 rounded-lg p-3 border border-slate-200 flex items-center justify-between">
          <div>
            <span class="text-slate-600 font-medium">Estimasi Biaya Pengiriman:</span>
            <div class="text-slate-900 font-semibold text-sm mt-0.5">
              {{ estimatedCost ? `Rp ${Number(estimatedCost).toLocaleString('id-ID')}` : 'Pilih kurir & berat' }}
            </div>
          </div>
          <button
            type="button"
            @click="calculateRate"
            :disabled="calculatingRate"
            class="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-medium transition"
          >
            {{ calculatingRate ? 'Menghitung...' : 'Cek Tarif Live' }}
          </button>
        </div>

        <!-- Waybill / No Resi Input -->
        <div>
          <div class="flex justify-between items-center mb-1.5">
            <label class="block text-[10px] font-semibold text-slate-700 uppercase tracking-wider">
              Nomor Resi (Waybill AWB) *
            </label>
            <button
              type="button"
              @click="generateSimulatedWaybill"
              class="text-sky-600 hover:text-sky-800 text-[11px] font-medium"
            >
              + Generate No. Resi Otomatis
            </button>
          </div>
          <input
            v-model="form.waybill_no"
            type="text"
            required
            class="w-full text-xs font-mono tracking-wider px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-slate-400 uppercase text-slate-900"
            placeholder="Contoh: JNE882910291039 / SICEPAT129381"
          />
          <p class="text-[11px] text-slate-400 mt-1">
            Resi akan otomatis dipantau oleh background sync Biteship.
          </p>
        </div>
      </div>

      <!-- Footer -->
      <div class="bg-slate-50 px-6 py-4 border-t border-slate-200 flex items-center justify-end space-x-2">
        <button
          type="button"
          @click="close"
          class="px-3.5 py-2 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-200 transition"
        >
          Batal
        </button>
        <button
          type="button"
          @click="submitDispatch"
          :disabled="submitting || !form.courier_code || !form.waybill_no"
          class="px-4 py-2 rounded-lg text-xs font-medium bg-sky-600 hover:bg-sky-700 text-white transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1.5"
        >
          <span v-if="submitting">Memproses...</span>
          <span v-else>Konfirmasi & Kirim Paket</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { Send, X } from 'lucide-vue-next'
import { DeliveryApi } from '@/api'

const props = defineProps({
  isOpen: Boolean,
  note: Object,
  couriers: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close', 'dispatched'])

const submitting = ref(false)
const calculatingRate = ref(false)
const estimatedCost = ref(12000)

const form = reactive({
  courier_code: 'jne',
  courier_service: 'REG',
  weight_grams: 1000,
  waybill_no: '',
  notes: '',
})

function selectCourier(c) {
  form.courier_code = c.code
  calculateRate()
}

async function calculateRate() {
  calculatingRate.value = true
  try {
    const rates = await DeliveryApi.estimateRates({
      courier_code: form.courier_code,
      weight_grams: form.weight_grams
    })
    if (rates && rates.length > 0) {
      estimatedCost.value = rates[0].price
    }
  } catch (err) {
    console.error('Rate calculation err:', err)
  } finally {
    calculatingRate.value = false
  }
}

function generateSimulatedWaybill() {
  const prefix = (form.courier_code || 'EXP').toUpperCase()
  const randomNum = Math.floor(1000000000 + Math.random() * 9000000000)
  form.waybill_no = `${prefix}${randomNum}`
}

async function submitDispatch() {
  if (!form.courier_code || !form.waybill_no) return
  submitting.value = true
  try {
    await DeliveryApi.dispatchEkspedisi({
      delivery_note: props.note.name,
      courier_code: form.courier_code,
      waybill_no: form.waybill_no,
      courier_service: form.courier_service,
      notes: form.notes
    })
    emit('dispatched')
    close()
  } catch (err) {
    alert(err.message || 'Gagal mengirim ekspedisi')
  } finally {
    submitting.value = false
  }
}

function close() {
  emit('close')
}

watch(() => props.isOpen, (open) => {
  if (open) {
    form.courier_code = props.note?.custom_courier_code || 'jne'
    form.waybill_no = props.note?.custom_waybill_no || ''
    form.weight_grams = 1000
    calculateRate()
  }
})
</script>