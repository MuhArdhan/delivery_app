<template>
  <div class="space-y-4">
    <!-- Top-Level Tab Navigation: Sales Order Intake vs Delivery Note Dispatch -->
    <div class="flex items-center space-x-2 border-b border-slate-200 pb-2">
      <button
        @click="switchMainTab('sales_orders')"
        :class="[
          'px-4 py-2 rounded-lg text-xs font-semibold transition flex items-center space-x-2',
          mainTab === 'sales_orders'
            ? 'bg-slate-900 text-white shadow-xs'
            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
        ]"
      >
        <FileText :size="14" />
        <span>Pesanan (Sales Order)</span>
        <span
          v-if="soReadyCount > 0"
          class="px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-sky-500 text-white"
        >
          {{ soReadyCount }}
        </span>
      </button>

      <button
        @click="switchMainTab('delivery_notes')"
        :class="[
          'px-4 py-2 rounded-lg text-xs font-semibold transition flex items-center space-x-2',
          mainTab === 'delivery_notes'
            ? 'bg-slate-900 text-white shadow-xs'
            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
        ]"
      >
        <Package :size="14" />
        <span>Surat Jalan (Delivery Note)</span>
        <span
          v-if="totalCount > 0"
          class="px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-200 text-slate-700"
        >
          {{ totalCount }}
        </span>
      </button>
    </div>

    <!-- ========================================== -->
    <!-- TAB 1: SALES ORDER INTAKE                  -->
    <!-- ========================================== -->
    <div v-if="mainTab === 'sales_orders'" class="space-y-4">
      <!-- SO Header with Filters -->
      <div class="bg-white rounded-xl p-5 border border-slate-200 space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 class="text-sm font-semibold text-slate-900 tracking-tight">Intake Pesanan (Sales Order)</h2>
            <p class="text-xs text-slate-500">Pilih Sales Order submitted untuk dibuatkan 1 Delivery Note penuh secara langsung</p>
          </div>
          <div class="flex items-center space-x-2">
            <button
              @click="refreshSalesOrders"
              :disabled="soLoading"
              class="px-3 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs font-medium text-slate-700 transition flex items-center space-x-1.5"
            >
              <RefreshCw :size="13" :class="soLoading ? 'animate-spin' : ''" />
              <span>{{ soLoading ? 'Memuat...' : 'Refresh' }}</span>
            </button>
          </div>
        </div>

        <!-- Filter Controls -->
        <div class="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 pt-3 border-t border-slate-100">
          <!-- Status Tabs -->
          <div class="flex items-center space-x-1 bg-slate-100 p-1 rounded-lg text-xs font-medium text-slate-600">
            <button
              v-for="tab in soStatusTabs"
              :key="tab.id"
              @click="changeSoTab(tab.id)"
              :class="[
                'px-3 py-1.5 rounded-md transition',
                soCurrentTab === tab.id ? 'bg-white text-slate-900 shadow-xs font-semibold' : 'hover:text-slate-900'
              ]"
            >
              {{ tab.label }}
            </button>
          </div>

          <!-- Company Filter & Search input -->
          <div class="flex items-center space-x-2">
            <select
              v-model="soCompanyFilter"
              @change="refreshSalesOrders"
              class="text-xs px-3 py-2 rounded-lg border border-slate-200 bg-white text-slate-700 focus:outline-none focus:border-slate-400"
            >
              <option value="">Semua Company</option>
              <option v-for="c in companyList" :key="c.name" :value="c.name">
                {{ c.company_name || c.name }}
              </option>
            </select>

            <div class="relative w-full md:w-64">
              <input
                v-model="soSearchQuery"
                @keyup.enter="refreshSalesOrders"
                type="text"
                placeholder="Cari no. SO, pelanggan, alamat..."
                class="w-full text-xs pl-8 pr-3 py-2 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:border-slate-400 transition"
              />
              <Search :size="13" class="absolute left-2.5 top-2.5 text-slate-400" />
            </div>
          </div>
        </div>
      </div>

      <!-- Sales Orders Table -->
      <div class="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse text-xs">
            <thead class="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
              <tr>
                <th class="p-3.5">No. Pesanan / Tanggal</th>
                <th class="p-3.5">Pelanggan & Tujuan</th>
                <th class="p-3.5">Barang & Nilai</th>
                <th class="p-3.5">Status Intake</th>
                <th class="p-3.5 text-right">Aksi Proses</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-if="soLoading && salesOrders.length === 0">
                <td colspan="5" class="p-8 text-center text-slate-400">
                  <RefreshCw :size="16" class="animate-spin inline mr-2 text-sky-600" />
                  Memuat daftar Sales Order...
                </td>
              </tr>
              <tr v-else-if="salesOrders.length === 0">
                <td colspan="5" class="p-12 text-center text-slate-400">
                  <FileText :size="24" class="mx-auto mb-2 text-slate-300" />
                  Tidak ada Sales Order yang sesuai kriteria filter.
                </td>
              </tr>
              <tr
                v-for="so in salesOrders"
                :key="so.name"
                class="hover:bg-slate-50/70 transition"
              >
                <!-- Order Name & Dates -->
                <td class="p-3.5">
                  <div class="font-bold text-slate-900 font-mono">{{ so.name }}</div>
                  <div class="text-[11px] text-slate-500 mt-0.5 flex items-center space-x-1">
                    <Calendar :size="11" class="text-slate-400" />
                    <span>Kirim: {{ formatDate(so.delivery_date) }}</span>
                  </div>
                  <div class="text-[10px] text-slate-400 mt-0.5 truncate max-w-[180px]">
                    {{ so.company }}
                  </div>
                </td>

                <!-- Customer & Address -->
                <td class="p-3.5 max-w-xs">
                  <div class="font-semibold text-slate-800">{{ so.customer_name || so.customer }}</div>
                  <div class="text-[11px] text-slate-500 truncate mt-0.5" :title="so.shipping_address">
                    {{ so.shipping_address || '-' }}
                  </div>
                  <div class="mt-1">
                    <span
                      :class="[
                        'inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-medium border',
                        so.has_coordinates
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : 'bg-slate-100 text-slate-500 border-slate-200'
                      ]"
                    >
                      <MapPin :size="9" />
                      <span>{{ so.has_coordinates ? 'Titik Terisi' : 'Titik Belum Ada' }}</span>
                    </span>
                  </div>
                </td>

                <!-- Items & Value -->
                <td class="p-3.5">
                  <div class="font-semibold text-slate-900">
                    Rp {{ formatCurrency(so.grand_total) }}
                  </div>
                  <div class="text-[11px] text-slate-500 mt-0.5">
                    {{ so.total_items }} Item ({{ so.total_qty }} Unit)
                  </div>
                </td>

                <!-- Intake Status -->
                <td class="p-3.5">
                  <span
                    :class="[
                      'inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border',
                      so.intake_status === 'ready'
                        ? 'bg-sky-50 text-sky-700 border-sky-200'
                        : so.intake_status === 'already_created'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-amber-50 text-amber-700 border-amber-200'
                    ]"
                  >
                    {{ so.intake_status_label }}
                  </span>
                  <div v-if="so.existing_dn" class="text-[10px] font-mono text-slate-500 mt-1">
                    DN: {{ so.existing_dn }}
                  </div>
                </td>

                <!-- Action Button -->
                <td class="p-3.5 text-right">
                  <button
                    v-if="so.is_eligible"
                    @click="openCreateDnModal(so.name)"
                    class="px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-medium transition inline-flex items-center space-x-1 shadow-xs"
                  >
                    <Plus :size="13" />
                    <span>Buat Delivery Note</span>
                  </button>

                  <button
                    v-else-if="so.existing_dn"
                    @click="switchMainTab('delivery_notes', so.existing_dn)"
                    class="px-2.5 py-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-medium transition inline-flex items-center space-x-1"
                  >
                    <span>Lihat di DN</span>
                    <ExternalLink :size="11" />
                  </button>

                  <span v-else class="text-[11px] text-slate-400 italic">
                    Lewat Desk
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- SO Pagination Footer -->
        <div class="px-5 py-3 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between text-xs text-slate-500">
          <div>
            Menampilkan <strong class="text-slate-800">{{ salesOrders.length }}</strong> dari <strong class="text-slate-800">{{ soTotalCount }}</strong> Pesanan
          </div>
          <div class="flex items-center space-x-2">
            <button
              @click="prevSoPage"
              :disabled="soCurrentPage <= 1 || soLoading"
              class="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition font-medium inline-flex items-center space-x-1"
            >
              <ChevronLeft :size="13" />
              <span>Sebelumnya</span>
            </button>
            <span class="px-2 text-slate-700 font-semibold">Hal. {{ soCurrentPage }}</span>
            <button
              @click="nextSoPage"
              :disabled="salesOrders.length < soPageSize || soLoading"
              class="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition font-medium inline-flex items-center space-x-1"
            >
              <span>Selanjutnya</span>
              <ChevronRight :size="13" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ========================================== -->
    <!-- TAB 2: DELIVERY NOTE DISPATCH              -->
    <!-- ========================================== -->
    <div v-else class="space-y-4">
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
              class="px-3.5 py-2 rounded-lg bg-sky-600 hover:bg-sky-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-medium transition flex items-center space-x-1.5 shadow-xs"
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
              <tr v-if="loading && notes.length === 0">
                <td colspan="7" class="p-8 text-center text-slate-400">
                  <RefreshCw :size="16" class="animate-spin inline mr-2 text-sky-600" />
                  Memuat daftar surat jalan...
                </td>
              </tr>
              <tr v-else-if="notes.length === 0">
                <td colspan="7" class="p-12 text-center text-slate-400">
                  <Package :size="24" class="mx-auto mb-2 text-slate-300" />
                  Tidak ada pengiriman yang sesuai kriteria filter.
                </td>
              </tr>
              <tr
                v-for="note in notes"
                :key="note.name"
                :class="[
                  'hover:bg-slate-50/70 transition',
                  isSelected(note) ? 'bg-sky-50/40' : ''
                ]"
              >
                <!-- Select Checkbox -->
                <td class="p-3.5 text-center">
                  <input
                    type="checkbox"
                    :checked="isSelected(note)"
                    @change="toggleSelect(note)"
                    :disabled="note.custom_delivery_method === 'Ekspedisi' || note.trip"
                    class="rounded border-slate-300 text-sky-600 focus:ring-0 w-3.5 h-3.5 cursor-pointer disabled:opacity-20 disabled:cursor-not-allowed"
                  />
                </td>

                <!-- Document ID & Date -->
                <td class="p-3.5">
                  <div
                    @click="openDrawer(note)"
                    class="font-bold text-sky-600 hover:text-sky-800 cursor-pointer font-mono"
                  >
                    {{ note.name }}
                  </div>
                  <div class="text-[11px] text-slate-500 mt-0.5 flex items-center space-x-1">
                    <Calendar :size="11" class="text-slate-400" />
                    <span>{{ formatDate(note.posting_date) }}</span>
                  </div>
                </td>

                <!-- Customer & Address -->
                <td class="p-3.5 max-w-xs">
                  <div class="font-semibold text-slate-800">{{ note.customer_name || note.customer }}</div>
                  <div class="text-[11px] text-slate-500 truncate mt-0.5" :title="note.address_display || note.shipping_address">
                    {{ note.address_display || note.shipping_address || '-' }}
                  </div>
                </td>

                <!-- Items & Value -->
                <td class="p-3.5">
                  <div class="font-semibold text-slate-900">
                    Rp {{ formatCurrency(note.grand_total) }}
                  </div>
                  <div class="text-[11px] text-slate-500 mt-0.5">
                    {{ note.total_qty }} Unit Barang
                  </div>
                </td>

                <!-- Delivery Method Badge -->
                <td class="p-3.5">
                  <span
                    :class="[
                      'inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-medium border',
                      note.custom_delivery_method === 'Ekspedisi'
                        ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                        : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    ]"
                  >
                    <component :is="note.custom_delivery_method === 'Ekspedisi' ? Send : Truck" :size="12" />
                    <span>{{ note.custom_delivery_method || 'Armada Sendiri' }}</span>
                  </span>
                </td>

                <!-- Status Tracking / Fleet Trip -->
                <td class="p-3.5">
                  <!-- Case A: 3PL Ekspedisi -->
                  <div v-if="note.custom_delivery_method === 'Ekspedisi'">
                    <div class="flex items-center space-x-1.5">
                      <span class="font-semibold text-slate-800 uppercase">{{ note.custom_courier_code || '3PL' }}</span>
                      <span
                        v-if="note.custom_tracking_status"
                        :class="[
                          'px-1.5 py-0.5 rounded text-[10px] font-semibold border',
                          note.custom_tracking_status === 'Delivered'
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : 'bg-amber-50 text-amber-700 border-amber-200'
                        ]"
                      >
                        {{ note.custom_tracking_status }}
                      </span>
                    </div>
                    <div v-if="note.custom_waybill_no" class="font-mono text-[11px] text-slate-500 mt-0.5">
                      Resi: {{ note.custom_waybill_no }}
                    </div>
                    <div v-else class="text-[11px] text-rose-500 italic mt-0.5">
                      Belum ada nomor resi
                    </div>
                  </div>

                  <!-- Case B: Armada Sendiri -->
                  <div v-else>
                    <div v-if="note.trip" class="space-y-0.5">
                      <div class="font-medium text-slate-800 flex items-center space-x-1">
                        <Route :size="12" class="text-sky-600" />
                        <span class="font-mono text-[11px]">{{ note.trip.name }}</span>
                      </div>
                      <span
                        :class="[
                          'inline-block px-1.5 py-0.2 rounded text-[10px] font-medium border',
                          note.custom_pod_status === 'Delivered'
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : 'bg-sky-50 text-sky-700 border-sky-200'
                        ]"
                      >
                        {{ note.custom_pod_status || 'Dalam Rute' }}
                      </span>
                    </div>
                    <div v-else-if="note.custom_pod_status === 'Delivered'" class="text-emerald-600 font-medium flex items-center space-x-1">
                      <Check :size="12" />
                      <span>Terkirim</span>
                    </div>
                    <div v-else class="text-[11px] text-amber-600 font-medium">
                      Siap Dijadwalkan
                    </div>
                  </div>
                </td>

                <!-- Dispatch Actions -->
                <td class="p-3.5 text-right space-x-1.5">
                  <!-- Button for 3PL Dispatch modal -->
                  <button
                    v-if="note.custom_delivery_method === 'Ekspedisi' && !note.custom_waybill_no"
                    @click="openDispatchEkspedisi(note)"
                    class="px-2.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium transition inline-flex items-center space-x-1"
                  >
                    <Send :size="12" />
                    <span>Dispatch 3PL</span>
                  </button>

                  <!-- Button to schedule single note to Fleet Trip -->
                  <button
                    v-if="note.custom_delivery_method !== 'Ekspedisi' && !note.trip"
                    @click="openSingleTripModal(note)"
                    class="px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-medium transition inline-flex items-center space-x-1"
                  >
                    <Route :size="12" />
                    <span>Jadwalkan</span>
                  </button>

                  <!-- Button to view tracking timeline -->
                  <button
                    v-if="note.custom_waybill_no"
                    @click="openTrackingModal(note)"
                    class="px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 text-xs font-medium transition inline-flex items-center space-x-1"
                  >
                    <span>Pelacakan</span>
                  </button>

                  <!-- Button to view Proof of Delivery -->
                  <button
                    v-if="note.custom_proof_of_delivery || note.custom_pod_status === 'Delivered'"
                    @click="openPodModal(note)"
                    class="px-2.5 py-1.5 rounded-lg border border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 text-xs font-medium transition inline-flex items-center space-x-1"
                  >
                    <ShieldCheck :size="12" />
                    <span>POD</span>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- DN Pagination Footer -->
        <div class="px-5 py-3 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between text-xs text-slate-500">
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
    </div>

    <!-- Modals & Drawers -->
    <CreateDeliveryNoteModal
      :is-open="isCreateDnModalOpen"
      :sales-order-id="activeSalesOrderId"
      @close="isCreateDnModalOpen = false"
      @created="handleDnCreated"
    />

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
  ChevronRight,
  FileText,
  Package,
  Plus,
  MapPin,
  ExternalLink
} from 'lucide-vue-next'
import { DeliveryApi } from '@/api'
import CreateDeliveryNoteModal from '@/components/CreateDeliveryNoteModal.vue'
import DispatchEkspedisiModal from '@/components/DispatchEkspedisiModal.vue'
import CreateTripModal from '@/components/CreateTripModal.vue'
import TrackingTimelineModal from '@/components/TrackingTimelineModal.vue'
import PodDetailModal from '@/components/PodDetailModal.vue'
import DeliveryNoteDrawer from '@/components/DeliveryNoteDrawer.vue'

const mainTab = ref('sales_orders')

// Sales Order State
const soLoading = ref(false)
const salesOrders = ref([])
const soTotalCount = ref(0)
const soReadyCount = ref(0)
const soCurrentPage = ref(1)
const soPageSize = ref(20)
const soCurrentTab = ref('ready')
const soCompanyFilter = ref('')
const soSearchQuery = ref('')

const isCreateDnModalOpen = ref(false)
const activeSalesOrderId = ref(null)

const soStatusTabs = [
  { id: 'ready', label: 'Siap Diproses' },
  { id: 'all', label: 'Semua Pesanan' },
  { id: 'partial', label: 'Parsial' },
  { id: 'delivered', label: 'Selesai' },
]

// Delivery Note State
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
const companyList = ref([])
const courierList = ref([])

const statusTabs = [
  { id: 'Ready', label: 'Siap Kirim' },
  { id: 'In Transit', label: 'Dalam Pengiriman' },
  { id: 'Delivered', label: 'Terkirim (Selesai)' },
  { id: 'All', label: 'Semua' },
]

function switchMainTab(tab, searchTarget = null) {
  mainTab.value = tab
  if (tab === 'delivery_notes') {
    if (searchTarget) {
      searchQuery.value = searchTarget
      currentTab.value = 'All'
    }
    refreshNotes()
  } else {
    refreshSalesOrders()
  }
}

async function refreshSalesOrders() {
  soLoading.value = true
  try {
    const res = await DeliveryApi.getSalesOrders({
      company: soCompanyFilter.value || null,
      status_filter: soCurrentTab.value,
      search: soSearchQuery.value || null,
      page: soCurrentPage.value,
      page_size: soPageSize.value,
    })
    salesOrders.value = res.items || []
    soTotalCount.value = res.total_count || 0

    // Count ready items
    soReadyCount.value = (res.items || []).filter(i => i.is_eligible).length
  } catch (err) {
    console.error('Failed to load sales orders:', err)
  } finally {
    soLoading.value = false
  }
}

function changeSoTab(tabId) {
  soCurrentTab.value = tabId
  soCurrentPage.value = 1
  refreshSalesOrders()
}

function openCreateDnModal(soName) {
  activeSalesOrderId.value = soName
  isCreateDnModalOpen.value = true
}

function handleDnCreated(createdRes) {
  refreshSalesOrders()
  refreshNotes()
}

function prevSoPage() {
  if (soCurrentPage.value > 1) {
    soCurrentPage.value--
    refreshSalesOrders()
  }
}

function nextSoPage() {
  if (salesOrders.value.length >= soPageSize.value) {
    soCurrentPage.value++
    refreshSalesOrders()
  }
}

const isAllSelected = computed(() => {
  const eligible = notes.value.filter(n => n.custom_delivery_method !== 'Ekspedisi' && !n.trip)
  return eligible.length > 0 && selectedNotes.value.length === eligible.length
})

function isSelected(note) {
  return selectedNotes.value.some(n => n.name === note.name)
}

function toggleSelect(note) {
  const idx = selectedNotes.value.findIndex(n => n.name === note.name)
  if (idx > -1) {
    selectedNotes.value.splice(idx, 1)
  } else {
    selectedNotes.value.push(note)
  }
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
    companyList.value = res.companies || []
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

function formatDate(val) {
  if (!val) return '-'
  try {
    const d = new Date(val)
    return d.toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return val
  }
}

function formatCurrency(val) {
  return Number(val || 0).toLocaleString('id-ID')
}

onMounted(() => {
  loadResources()
  refreshSalesOrders()
  refreshNotes()
})
</script>
