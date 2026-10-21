<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 overflow-y-auto bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4">
    <div class="relative bg-white rounded-xl shadow-xl max-w-xl w-full border border-slate-200 overflow-hidden transform transition-all">
      <!-- Header -->
      <div class="bg-slate-900 text-white px-6 py-4 flex items-center justify-between border-b border-slate-800">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-200">
            <ShieldCheck :size="15" class="text-emerald-400" />
          </div>
          <div>
            <h3 class="font-semibold text-sm text-white">Proof of Delivery (POD)</h3>
            <p class="text-xs text-slate-400">{{ pod?.delivery_note || note?.name }} · Bukti Serah Terima</p>
          </div>
        </div>
        <button @click="close" class="text-slate-400 hover:text-white p-1 rounded-lg transition">
          <X :size="16" />
        </button>
      </div>

      <!-- Body -->
      <div class="p-6 space-y-5 max-h-[80vh] overflow-y-auto text-xs">
        <!-- Delivery info -->
        <div class="grid grid-cols-2 gap-3 p-3.5 bg-slate-50 border border-slate-200 rounded-lg text-xs">
          <div>
            <span class="text-slate-400 block text-[11px]">Penerima Barang:</span>
            <span class="font-semibold text-slate-800 text-sm">{{ pod?.recipient_name || '-' }}</span>
            <span class="text-slate-500 block text-[11px] mt-0.5">{{ pod?.recipient_relationship || 'Yang Bersangkutan' }}</span>
          </div>
          <div>
            <span class="text-slate-400 block text-[11px]">Waktu Serah Terima:</span>
            <span class="font-medium text-slate-700">{{ pod?.submitted_at || '-' }}</span>
            <span v-if="pod?.recipient_phone" class="text-slate-500 inline-flex items-center space-x-1 text-[11px] mt-0.5">
              <Phone :size="11" class="text-slate-400" />
              <span>{{ pod?.recipient_phone }}</span>
            </span>
          </div>
        </div>

        <!-- Photo & Signature Viewers -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <!-- Photo -->
          <div>
            <span class="text-[10px] font-semibold text-slate-700 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
              <Camera :size="13" class="text-slate-500" />
              <span>Foto Bukti di Lokasi</span>
            </span>
            <div class="aspect-video sm:aspect-square bg-slate-100 border border-slate-200 rounded-lg overflow-hidden flex items-center justify-center">
              <img
                v-if="pod?.proof_photo"
                :src="pod.proof_photo"
                alt="Foto POD"
                class="w-full h-full object-cover cursor-pointer hover:scale-102 transition duration-200"
                @click="openImage(pod.proof_photo)"
              />
              <span v-else class="text-xs text-slate-400">Tidak ada foto</span>
            </div>
          </div>

          <!-- Signature -->
          <div>
            <span class="text-[10px] font-semibold text-slate-700 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
              <PenTool :size="13" class="text-slate-500" />
              <span>Tanda Tangan Digital</span>
            </span>
            <div class="aspect-video sm:aspect-square bg-white border border-slate-200 rounded-lg overflow-hidden flex items-center justify-center p-3">
              <img
                v-if="pod?.signature"
                :src="pod.signature"
                alt="Tanda Tangan"
                class="max-w-full max-h-full object-contain"
              />
              <span v-else class="text-xs text-slate-400">Tidak ada tanda tangan</span>
            </div>
          </div>
        </div>

        <!-- Geolocation coordinates -->
        <div v-if="pod?.latitude && pod?.longitude" class="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between text-xs">
          <div class="flex items-center space-x-2">
            <MapPin :size="13" class="text-slate-500" />
            <span class="text-slate-600 font-medium">Koordinat GPS:</span>
            <span class="font-mono text-slate-800">{{ pod.latitude.toFixed(5) }}, {{ pod.longitude.toFixed(5) }}</span>
          </div>
          <a
            :href="`https://www.google.com/maps?q=${pod.latitude},${pod.longitude}`"
            target="_blank"
            class="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-white rounded-md font-medium transition inline-flex items-center space-x-1 text-[11px]"
          >
            <span>Buka Maps</span>
            <ExternalLink :size="10" />
          </a>
        </div>

        <div v-if="pod?.notes" class="text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-200">
          <span class="font-medium text-slate-700 block mb-1">Catatan Pengantaran:</span>
          {{ pod.notes }}
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
import { ShieldCheck, X, Phone, Camera, PenTool, MapPin, ExternalLink } from 'lucide-vue-next'

const props = defineProps({
  isOpen: Boolean,
  pod: Object,
  note: Object
})

const emit = defineEmits(['close'])

function openImage(url) {
  if (url) window.open(url, '_blank')
}

function close() {
  emit('close')
}
</script>