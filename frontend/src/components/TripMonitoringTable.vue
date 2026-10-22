<template>
  <div class="overflow-x-auto rounded-xl border border-slate-200 bg-white">
    <table class="w-full text-left text-sm text-slate-700">
      <thead class="bg-slate-50 text-xs text-slate-500">
        <tr><th class="p-3">Trip / Company</th><th class="p-3">Pengemudi / Plat</th><th class="p-3">Jadwal / Berangkat aktual</th><th class="p-3">Progres</th><th class="p-3">Konfirmasi terakhir</th><th class="p-3">Status</th><th class="p-3">Aksi</th></tr>
      </thead>
      <tbody class="divide-y divide-slate-100">
        <tr v-for="trip in trips" :key="trip.name" class="hover:bg-slate-50">
          <td class="p-3"><button @click="$emit('select', trip)" class="text-sky-700 font-medium hover:underline">{{ trip.name }}</button><p class="text-xs text-slate-500">{{ trip.company }}</p></td>
          <td class="p-3">{{ trip.driver_name || trip.driver }}<p class="text-xs text-slate-500">{{ trip.vehicle }}</p></td>
          <td class="p-3 text-xs">{{ trip.departure_time || '-' }}<p class="text-slate-500 mt-1">Aktual: {{ trip.custom_actual_departure || 'Belum tercatat' }}</p></td>
          <td class="p-3 whitespace-nowrap">{{ trip.completed_stops }} / {{ trip.total_stops }}</td>
          <td class="p-3 text-xs">{{ trip.last_checkpoint?.text || 'Belum tersedia' }}</td>
          <td class="p-3"><span class="rounded border border-slate-200 px-2 py-1 text-xs whitespace-nowrap">{{ trip.monitoring_status }}</span></td>
          <td class="p-3"><div class="flex gap-2">
            <button @click="$emit('select', trip)" class="text-sky-700 hover:underline whitespace-nowrap">Detail & rute</button>
            <button v-if="trip.docstatus === 1 && !trip.custom_actual_departure && trip.monitoring_status !== 'Selesai Kunjungan'" @click="$emit('depart', trip.name)" class="text-sky-700 hover:underline">Berangkat</button>
          </div></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
defineProps({ trips: { type: Array, default: () => [] } })
defineEmits(['select', 'depart'])
</script>
