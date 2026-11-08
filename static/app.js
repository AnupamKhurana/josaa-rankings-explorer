// ==========================================================================
// APP LOGIC: JoSAA & JAC Delhi Rankings Explorer
// ==========================================================================

// Global state
let state = {
    year: "2025",
    round: "6",
    seatType: "OPNO",
    search: "",
    quotas: [],
    gender: "Gender-Neutral",
    minOpening: 1,
    maxOpening: 100000,
    minClosing: 1,
    maxClosing: 100000,
    sortBy: "closing_rank",
    sortDesc: false,
    rankMains: 0,
    rankAdv: 0,
    chkFilterMains: false,
    chkFilterAdv: false,
    mainsMin: 1,
    advMin: 1,
    homeState: "ALL",
    page: 1,
    limit: 100000,
    total: 0,
    activeTab: "josaa",
    instType: "ALL"
};

// UI Elements
const els = {
    selectRound: document.getElementById('select-round'),
    selectSeatType: document.getElementById('select-seat-type'),
    btnFetchRanks: document.getElementById('btn-fetch-ranks'),
    searchInput: document.getElementById('search-input'),
    filterQuota: document.getElementById('filter-quota'),
    filterGender: document.getElementById('filter-gender'),
    filterInstType: document.getElementById('filter-inst-type'),
    
    // Sliders
    sliderMinOpening: document.getElementById('slider-min-opening'),
    sliderMaxOpening: document.getElementById('slider-max-opening'),
    sliderMinClosing: document.getElementById('slider-min-closing'),
    sliderMaxClosing: document.getElementById('slider-max-closing'),
    
    // Number Inputs
    inputMinOpening: document.getElementById('input-min-opening'),
    inputMaxOpening: document.getElementById('input-max-opening'),
    inputMinClosing: document.getElementById('input-min-closing'),
    inputMaxClosing: document.getElementById('input-max-closing'),
    
    btnResetFilters: document.getElementById('btn-reset-filters'),
    
    // Stats
    statTotalInstitutes: document.getElementById('stat-total-institutes'),
    statTotalPrograms: document.getElementById('stat-total-programs'),
    statOpeningMin: document.getElementById('stat-opening-min'),
    statTotalRecords: document.getElementById('stat-total-records'),
    
    // Table
    ranksTable: document.getElementById('ranks-table'),
    ranksTbody: document.getElementById('ranks-tbody'),
    tableLoadingOverlay: document.getElementById('table-loading-overlay'),
    tableEmptyState: document.getElementById('table-empty-state'),
    filteredRecordsCount: document.getElementById('filtered-records-count'),
    btnExportCsv: document.getElementById('btn-export-csv'),
    
    // Theme & Sidebar
    btnToggleTheme: document.getElementById('btn-toggle-theme'),
    dataStatusBadge: document.getElementById('data-status-badge'),
    
    // User Profile Ranks Displays
    rankMainsDisplay: document.getElementById('display-rank-mains'),
    rankAdvDisplay: document.getElementById('display-rank-adv'),
    homeStateDisplay: document.getElementById('display-home-state'),
    btnEditProfile: document.getElementById('btn-edit-profile'),
    chkFilterMains: document.getElementById('chk-filter-mains'),
    chkFilterAdv: document.getElementById('chk-filter-adv'),
    
    // Profile Modal
    profileModal: document.getElementById('profile-modal'),
    modalRankMains: document.getElementById('modal-rank-mains'),
    modalRankAdv: document.getElementById('modal-rank-adv'),
    modalSelectHomeState: document.getElementById('modal-select-home-state'),
    btnCancelProfile: document.getElementById('btn-cancel-profile'),
    btnSaveProfile: document.getElementById('btn-save-profile'),
    
    // Mains & Adv edit inputs
    inputMainsMin: document.getElementById('input-mains-min'),
    inputAdvMin: document.getElementById('input-adv-min'),
    
    // Scrape Modal
    scrapeModal: document.getElementById('scrape-modal'),
    modalProgressFill: document.getElementById('modal-progress-fill')
};

// Debounce helper
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Format numbers
function formatNumber(num) {
    if (num === undefined || num === null) return "-";
    if (num >= 999999) return "Prep / N/A";
    return num.toLocaleString('en-IN');
}

// Update Round dropdown choices dynamically
function updateRoundDropdown() {
    const maxRounds = 6;
    const roundSelect = els.selectRound;
    if (!roundSelect) return;
    
    const currentRound = roundSelect.value || state.round;
    roundSelect.innerHTML = "";
    
    for (let r = 1; r <= maxRounds; r++) {
        const opt = document.createElement('option');
        opt.value = String(r);
        opt.textContent = `Round ${r}`;
        roundSelect.appendChild(opt);
    }
    
    if (parseInt(currentRound) > maxRounds) {
        roundSelect.value = String(maxRounds);
        state.round = String(maxRounds);
    } else {
        roundSelect.value = currentRound;
        state.round = currentRound;
    }
}

// Initial initialization
document.addEventListener('DOMContentLoaded', () => {
    setupTheme();
    updateRoundDropdown();
    setupEventListeners();
    setupTabs();
    loadDataset();
});

// Setup event handlers
function setupEventListeners() {
    // Source data selectors
    els.selectRound.addEventListener('change', (e) => {
        state.round = e.target.value;
        loadDataset();
    });
    els.selectSeatType.addEventListener('change', (e) => {
        state.seatType = e.target.value;
        loadDataset();
    });
    
    // Fetch manual scrape trigger
    if (els.btnFetchRanks) {
        els.btnFetchRanks.addEventListener('click', triggerManualScrape);
    }
    
    // Filters
    els.searchInput.addEventListener('input', debounce((e) => {
        state.search = e.target.value;
        state.page = 1;
        fetchRanks();
    }, 300));
    
    els.filterQuota.addEventListener('change', (e) => {
        const selected = Array.from(els.filterQuota.selectedOptions).map(opt => opt.value);
        
        if (selected.includes("ALL")) {
            if (selected[selected.length - 1] === "ALL") {
                // If "ALL" was selected last, deselect everything else
                Array.from(els.filterQuota.options).forEach(opt => {
                    if (opt.value !== "ALL") opt.selected = false;
                });
                state.quotas = [];
            } else {
                // If something else was selected while "ALL" was selected, deselect "ALL"
                Array.from(els.filterQuota.options).forEach(opt => {
                    if (opt.value === "ALL") opt.selected = false;
                });
                state.quotas = selected.filter(v => v !== "ALL");
            }
        } else {
            state.quotas = selected;
        }
        
        // If nothing is selected, default back to selecting "ALL"
        if (els.filterQuota.selectedIndex === -1) {
            const allOpt = Array.from(els.filterQuota.options).find(opt => opt.value === "ALL");
            if (allOpt) allOpt.selected = true;
            state.quotas = [];
        }
        
        state.page = 1;
        fetchRanks();
    });
    
    els.filterGender.addEventListener('change', (e) => {
        state.gender = e.target.value;
        state.page = 1;
        fetchRanks();
    });
    
    els.filterInstType.addEventListener('change', (e) => {
        state.instType = e.target.value;
        state.page = 1;
        fetchRanks();
    });
    
    // Range sliders linking & events
    setupRangeSliders();
    
    // Reset filters
    els.btnResetFilters.addEventListener('click', resetFilters);
    
    // Sorting headers
    document.querySelectorAll('th.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const field = th.dataset.sort;
            if (state.sortBy === field) {
                state.sortDesc = !state.sortDesc;
            } else {
                state.sortBy = field;
                state.sortDesc = false;
            }
            
            // Update UI headers
            document.querySelectorAll('th.sortable').forEach(header => {
                header.querySelector('i').className = 'fa-solid fa-sort';
            });
            const icon = th.querySelector('i');
            icon.className = state.sortDesc ? 'fa-solid fa-sort-down' : 'fa-solid fa-sort-up';
            
            state.page = 1;
            fetchRanks();
        });
    });
    
    // User Profile Modal Event Listeners
    els.btnEditProfile.addEventListener('click', () => {
        showProfileModal(false);
    });
    els.btnSaveProfile.addEventListener('click', () => {
        saveProfile();
    });
    els.btnCancelProfile.addEventListener('click', () => {
        cancelProfile();
    });
    els.chkFilterMains.addEventListener('change', (e) => {
        state.chkFilterMains = e.target.checked;
        localStorage.setItem('chkFilterMains', state.chkFilterMains);
        document.getElementById('mains-range-display').style.display = state.chkFilterMains ? 'block' : 'none';
        if (state.chkFilterMains) {
            if (state.mainsMin <= 1 && state.rankMains > 0) {
                updateClosingRankRangeFromMains();
            }
        }
        fetchRanks();
    });
    els.chkFilterAdv.addEventListener('change', (e) => {
        state.chkFilterAdv = e.target.checked;
        localStorage.setItem('chkFilterAdv', state.chkFilterAdv);
        document.getElementById('adv-range-display').style.display = state.chkFilterAdv ? 'block' : 'none';
        if (state.chkFilterAdv) {
            if (state.advMin <= 1 && state.rankAdv > 0) {
                updateClosingRankRangeFromAdv();
            }
        }
        fetchRanks();
    });

    // Mains & Adv range custom input handlers
    const attachCustomInputListeners = (inputEl, stateKey, storageKey) => {
        inputEl.addEventListener('change', () => {
            let val = parseInt(inputEl.value);
            if (isNaN(val) || val < 1) val = 1;
            state[stateKey] = val;
            inputEl.value = val;
            localStorage.setItem(storageKey, val);
            state.page = 1;
            fetchRanks();
        });
        
        inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                inputEl.blur();
            }
        });
    };
    
    attachCustomInputListeners(els.inputMainsMin, 'mainsMin', 'mainsMin');
    attachCustomInputListeners(els.inputAdvMin, 'advMin', 'advMin');
    
    // Theme toggle
    els.btnToggleTheme.addEventListener('click', toggleTheme);
    
    // Export CSV
    els.btnExportCsv.addEventListener('click', exportCSV);
}

// Helpers to compute and sync closing rank range inputs
function updateClosingRankRangeFromMains() {
    if (state.rankMains > 0) {
        const minBound = Math.round(state.rankMains * 0.9);
        state.mainsMin = minBound;
        els.inputMainsMin.value = minBound;
        localStorage.setItem('mainsMin', minBound);
    }
}

// Helpers to compute and sync closing rank range inputs
function updateClosingRankRangeFromAdv() {
    if (state.rankAdv > 0) {
        const minBound = Math.round(state.rankAdv * 0.9);
        state.advMin = minBound;
        els.inputAdvMin.value = minBound;
        localStorage.setItem('advMin', minBound);
    }
}

// Dual range slider implementation logic
function setupRangeSliders() {
    // Opening rank slider sync to inputs
    els.sliderMinOpening.addEventListener('input', () => {
        let valMin = parseInt(els.sliderMinOpening.value);
        let valMax = parseInt(els.sliderMaxOpening.value);
        if (valMin > valMax) {
            els.sliderMinOpening.value = valMax;
            valMin = valMax;
        }
        els.inputMinOpening.value = valMin;
        state.minOpening = valMin;
        triggerFilterUpdate();
    });
    
    els.sliderMaxOpening.addEventListener('input', () => {
        let valMin = parseInt(els.sliderMinOpening.value);
        let valMax = parseInt(els.sliderMaxOpening.value);
        if (valMax < valMin) {
            els.sliderMaxOpening.value = valMin;
            valMax = valMin;
        }
        els.inputMaxOpening.value = valMax;
        state.maxOpening = valMax;
        triggerFilterUpdate();
    });
    
    // Closing rank slider sync to inputs
    els.sliderMinClosing.addEventListener('input', () => {
        let valMin = parseInt(els.sliderMinClosing.value);
        let valMax = parseInt(els.sliderMaxClosing.value);
        if (valMin > valMax) {
            els.sliderMinClosing.value = valMax;
            valMin = valMax;
        }
        els.inputMinClosing.value = valMin;
        state.minClosing = valMin;
        triggerFilterUpdate();
    });
    
    els.sliderMaxClosing.addEventListener('input', () => {
        let valMin = parseInt(els.sliderMinClosing.value);
        let valMax = parseInt(els.sliderMaxClosing.value);
        if (valMax < valMin) {
            els.sliderMaxClosing.value = valMin;
            valMax = valMin;
        }
        els.inputMaxClosing.value = valMax;
        state.maxClosing = valMax;
        triggerFilterUpdate();
    });

    // Helper to process range input commits on blur / enter
    const handleInputCommit = (inputEl, sliderEl, isMin, isOpening) => {
        let val = parseInt(inputEl.value);
        let limitMin = parseInt(sliderEl.min) || 1;
        let limitMax = parseInt(sliderEl.max) || 100000;
        
        if (isNaN(val)) {
            // Default to limits if empty
            val = isMin ? limitMin : limitMax;
        }

        if (isMin) {
            let currentMax = isOpening ? state.maxOpening : state.maxClosing;
            if (val > currentMax) val = currentMax;
            if (val < limitMin) val = limitMin;
            if (isOpening) state.minOpening = val; else state.minClosing = val;
        } else {
            let currentMin = isOpening ? state.minOpening : state.minClosing;
            if (val < currentMin) val = currentMin;
            if (val > limitMax) val = limitMax;
            if (isOpening) state.maxOpening = val; else state.maxClosing = val;
        }
        
        inputEl.value = val;
        sliderEl.value = val;
        state.page = 1;
        fetchRanks();
    };

    const attachInputListeners = (inputEl, sliderEl, isMin, isOpening) => {
        inputEl.addEventListener('change', () => {
            handleInputCommit(inputEl, sliderEl, isMin, isOpening);
        });
        
        inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                inputEl.blur(); // Blurring triggers 'change' event immediately
            }
        });
    };

    attachInputListeners(els.inputMinOpening, els.sliderMinOpening, true, true);
    attachInputListeners(els.inputMaxOpening, els.sliderMaxOpening, false, true);
    attachInputListeners(els.inputMinClosing, els.sliderMinClosing, true, false);
    attachInputListeners(els.inputMaxClosing, els.sliderMaxClosing, false, false);
}

const triggerFilterUpdate = debounce(() => {
    state.page = 1;
    fetchRanks();
}, 450);

// Load filters and dataset ranks
async function loadDataset() {
    showLoading(true);
    try {
        // Fetch filters
        const resFilters = await fetch(`/api/filters?round=${state.round}&seat_type=${state.seatType}`);
        const filterData = await resFilters.json();
        
        // Populate Quota multi-select dropdown
        els.filterQuota.innerHTML = "";
        
        // Add ALL option at the top
        const allOpt = document.createElement('option');
        allOpt.value = "ALL";
        allOpt.textContent = "All Quotas";
        allOpt.selected = true;
        els.filterQuota.appendChild(allOpt);
        
        filterData.quotas.forEach(q => {
            const opt = document.createElement('option');
            opt.value = q;
            opt.textContent = q;
            els.filterQuota.appendChild(opt);
        });
        
        // Populate slider ranges from stats
        const stats = filterData.rank_stats;
        
        els.sliderMinOpening.min = stats.min_opening;
        els.sliderMinOpening.max = stats.max_opening;
        els.sliderMaxOpening.min = stats.min_opening;
        els.sliderMaxOpening.max = stats.max_opening;
        
        els.sliderMinClosing.min = stats.min_closing;
        els.sliderMinClosing.max = stats.max_closing;
        els.sliderMaxClosing.min = stats.min_closing;
        els.sliderMaxClosing.max = stats.max_closing;
        
        // Reset state slider values to full range
        els.sliderMinOpening.value = stats.min_opening;
        els.sliderMaxOpening.value = stats.max_opening;
        els.sliderMinClosing.value = stats.min_closing;
        els.sliderMaxClosing.value = stats.max_closing;
        
        state.minOpening = stats.min_opening;
        state.maxOpening = stats.max_opening;
        state.minClosing = stats.min_closing;
        state.maxClosing = stats.max_closing;
        
        els.inputMinOpening.value = stats.min_opening;
        els.inputMaxOpening.value = stats.max_opening;
        els.inputMinClosing.value = stats.min_closing;
        els.inputMaxClosing.value = stats.max_closing;
        
        // Fetch Ranks
        await fetchRanks();
        
        // Update stats summary on dashboard
        els.statTotalInstitutes.textContent = filterData.institutes.length;
        els.statTotalPrograms.textContent = filterData.programs.length;
        els.statOpeningMin.textContent = formatNumber(stats.min_opening);
        
    } catch (e) {
        console.error("Error loading JoSAA dataset:", e);
    } finally {
        showLoading(false);
    }
}

// Fetch ranks based on current state parameters
async function fetchRanks() {
    showTableLoading(true);
    try {
        let url = `/api/ranks?round_no=${state.round}&seat_type=${state.seatType}`;
        url += `&page=${state.page}&limit=${state.limit}`;
        url += `&sort_by=${state.sortBy}&sort_desc=${state.sortDesc}`;
        
        if (state.search) url += `&search=${encodeURIComponent(state.search)}`;
        if (state.gender && state.gender !== "ALL") url += `&gender=${encodeURIComponent(state.gender)}`;
        
        if (state.quotas.length > 0) {
            state.quotas.forEach(q => url += `&quota=${encodeURIComponent(q)}`);
        }
        
        url += `&min_opening=${state.minOpening}&max_opening=${state.maxOpening}`;
        url += `&min_closing=${state.minClosing}&max_closing=${state.maxClosing}`;
        
        // Custom Entrance Rank filters
        url += `&mains_min=${state.mainsMin}`;
        url += `&adv_min=${state.advMin}`;
        url += `&filter_mains=${state.chkFilterMains}&filter_adv=${state.chkFilterAdv}`;
        url += `&home_state=${state.homeState}`;
        url += `&user_mains_rank=${state.rankMains || 0}&user_adv_rank=${state.rankAdv || 0}`;
        
        const res = await fetch(url);
        const data = await res.json();
        
        let displayRanks = data.ranks;
        
        state.total = displayRanks.length;
        els.statTotalRecords.textContent = formatNumber(displayRanks.length);
        els.filteredRecordsCount.textContent = `Showing ${formatNumber(displayRanks.length)} records`;
        
        renderTable(displayRanks, data.rounds_used);
        
    } catch (e) {
        console.error("Error fetching ranking records:", e);
    } finally {
        showTableLoading(false);
    }
}

// Helper to categorize institute type
function getInstituteType(instName) {
    const norm = instName.toLowerCase();
    if (norm.includes('indian institute of technology') || norm.includes('indian institute  of technology') || norm.includes('iit ') || norm.includes('iit,')) {
        return 'IIT';
    }
    if (norm.includes('national institute of technology') || norm.includes('nit ') || norm.includes('nit,')) {
        return 'NIT';
    }
    if (norm.includes('iiit') || norm.includes('indian institute of information technology')) {
        return 'IIIT';
    }
    return 'GFTI';
}

// Render dynamic rows
function renderTable(ranks, roundsUsed) {
    els.ranksTbody.innerHTML = "";
    
    if (ranks.length === 0) {
        els.tableEmptyState.classList.remove('d-none');
        return;
    }
    
    els.tableEmptyState.classList.add('d-none');
    
    const selectedRoundNum = parseInt(state.round);
    
    ranks.forEach(r => {
        const row = document.createElement('tr');
        
        const nirfBadge = r.nirf_rank ? `<span class="badge badge-nirf" style="margin-left: 6px; font-size: 10px; padding: 2px 6px; background: rgba(245, 158, 11, 0.15); color: var(--warning); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 4px; font-weight: 600; display: inline-flex; align-items: center; gap: 3px;"><i class="fa-solid fa-trophy" style="font-size: 8px;"></i> NIRF #${r.nirf_rank}</span>` : '';
        const iirfBadge = r.iirf_rank ? `<span class="badge badge-iirf" style="margin-left: 6px; font-size: 10px; padding: 2px 6px; background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 4px; font-weight: 600; display: inline-flex; align-items: center; gap: 3px;"><i class="fa-solid fa-medal" style="font-size: 8px;"></i> IIRF #${r.iirf_rank}</span>` : '';
        
        // Helper to format rank with round info
        const formatRankCell = (rankVal, year) => {
            let formatted = formatNumber(rankVal);
            if (rankVal && rankVal < 999999 && roundsUsed && roundsUsed[year] !== selectedRoundNum) {
                formatted += ` <span style="font-size: 10px; font-weight: 700; padding: 1px 4px; background: rgba(245, 158, 11, 0.15); color: var(--warning); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 3px; margin-left: 4px; display: inline-block; vertical-align: middle;" title="Dataset only has ${roundsUsed[year]} rounds. Showing Round ${roundsUsed[year]} cutoff.">R${roundsUsed[year]}</span>`;
            }
            return formatted;
        };

        row.innerHTML = `
            <td>${r.institute}${nirfBadge}${iirfBadge}</td>
            <td>${r.program}</td>
            <td><span class="badge badge-outline">${r.quota}</span></td>
            <td>${r.gender}</td>
            <td>${formatNumber(r.opening_2025)}</td>
            <td>${formatRankCell(r.closing_2025, "2025")}</td>
            <td>${(function() {
                if (r.standardized_ratio !== undefined && r.standardized_ratio !== null) {
                    const ratioVal = r.standardized_ratio;
                    const formattedRatio = ratioVal.toFixed(2) + 'x';
                    const isSafe = ratioVal >= 1.0;
                    const color = isSafe ? '#10b981' : '#f87171';
                    const statusText = isSafe ? 'Safe / Within Reach' : 'Ambitious';
                    const refRankName = r.exam_type === 'JEE-Advanced' ? 'JEE Advanced' : 'JEE Main';
                    const refRankVal = r.exam_type === 'JEE-Advanced' ? state.rankAdv : state.rankMains;
                    const tooltipTitle = `Closing Rank: ${formatNumber(r.closing_rank)} vs Your ${refRankName} Rank: ${formatNumber(refRankVal)} (${statusText})`;
                    return `<span style="color: ${color}; font-weight: 600;" title="${tooltipTitle}">${formattedRatio}</span>`;
                }
                return '-';
            })()}</td>
            <td>${formatRankCell(r.closing_2024, "2024")}</td>
            <td>${formatRankCell(r.closing_2023, "2023")}</td>
            <td>${formatRankCell(r.closing_2022, "2022")}</td>
        `;
        
        els.ranksTbody.appendChild(row);
    });
}



// Reset filters to original range
function resetFilters() {
    els.searchInput.value = "";
    state.search = "";
    
    // Clear Quota selection (set back to All Quotas)
    Array.from(els.filterQuota.options).forEach(opt => {
        opt.selected = (opt.value === "ALL");
    });
    state.quotas = [];
    
    els.filterGender.value = "Gender-Neutral";
    state.gender = "Gender-Neutral";
    
    // Reset ranges to boundaries
    els.sliderMinOpening.value = els.sliderMinOpening.min;
    els.sliderMaxOpening.value = els.sliderMaxOpening.max;
    els.sliderMinClosing.value = els.sliderMinClosing.min;
    els.sliderMaxClosing.value = els.sliderMaxClosing.max;
    
    state.minOpening = parseInt(els.sliderMinOpening.min);
    state.maxOpening = parseInt(els.sliderMaxOpening.max);
    state.minClosing = parseInt(els.sliderMinClosing.min);
    state.maxClosing = parseInt(els.sliderMaxClosing.max);
    
    els.inputMinOpening.value = els.sliderMinOpening.min;
    els.inputMaxOpening.value = els.sliderMaxOpening.max;
    els.inputMinClosing.value = els.sliderMinClosing.min;
    els.inputMaxClosing.value = els.sliderMaxClosing.max;
    
    // Reset user ranks filters
    els.chkFilterMains.checked = false;
    els.chkFilterAdv.checked = false;
    state.chkFilterMains = false;
    state.chkFilterAdv = false;
    localStorage.removeItem('chkFilterMains');
    localStorage.removeItem('chkFilterAdv');
    document.getElementById('mains-range-display').style.display = 'none';
    document.getElementById('adv-range-display').style.display = 'none';
    
    state.mainsMin = 1;
    state.advMin = 1;
    
    els.inputMainsMin.value = "";
    els.inputAdvMin.value = "";
    
    localStorage.removeItem('mainsMin');
    localStorage.removeItem('advMin');
    
    els.filterInstType.value = "ALL";
    state.instType = "ALL";
    
    state.page = 1;
    fetchRanks();
}

// Trigger manual fetch overlay & scrape request
async function triggerManualScrape() {
    els.scrapeModal.classList.remove('d-none');
    els.modalProgressFill.style.width = '15%';
    
    const steps = [
        document.getElementById('step-0'),
        document.getElementById('step-1'),
        document.getElementById('step-2'),
        document.getElementById('step-3'),
        document.getElementById('step-4')
    ];
    
    // Helper to transition steps
    const setStep = (idx, status) => {
        if (status === 'running') {
            steps[idx].className = 'scrape-step';
            steps[idx].innerHTML = `<i class="fa-solid fa-circle-notch fa-spin text-accent"></i> ${steps[idx].textContent}`;
        } else if (status === 'success') {
            steps[idx].className = 'scrape-step text-success';
            steps[idx].innerHTML = `<i class="fa-solid fa-circle-check"></i> ${steps[idx].textContent.replace('...', '')}`;
        }
    };
    
    try {
        setStep(0, 'success');
        els.modalProgressFill.style.width = '30%';
        
        setStep(1, 'running');
        await new Promise(r => setTimeout(r, 600));
        setStep(1, 'success');
        els.modalProgressFill.style.width = '50%';
        
        setStep(2, 'running');
        await new Promise(r => setTimeout(r, 600));
        setStep(2, 'success');
        els.modalProgressFill.style.width = '70%';
        
        setStep(3, 'running');
        
        // Trigger server scrape request
        const res = await fetch('/api/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                year: "2025",
                round_no: state.round,
                seat_type: state.seatType
            })
        });
        
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Server failed to fetch rankings.");
        }
        
        setStep(3, 'success');
        els.modalProgressFill.style.width = '90%';
        
        setStep(4, 'running');
        await new Promise(r => setTimeout(r, 400));
        setStep(4, 'success');
        els.modalProgressFill.style.width = '100%';
        
        // Refresh dataset and UI filters
        await loadDataset();
        
        setTimeout(() => {
            els.scrapeModal.classList.add('d-none');
        }, 800);
        
    } catch (e) {
        alert(`Error scraping JoSAA page: ${e.message}\nThis happens when the admissions portal undergoes scheduled maintenance or responds with transient service errors. Please retry in a few moments.`);
        els.scrapeModal.classList.add('d-none');
    }
}

// Client-side CSV generation & export
async function exportCSV() {
    try {
        // Fetch all filtered records without limit
        let url = `/api/ranks?round_no=${state.round}&seat_type=${state.seatType}`;
        url += `&page=1&limit=1000000`; // large limit
        url += `&sort_by=${state.sortBy}&sort_desc=${state.sortDesc}`;
        
        if (state.search) url += `&search=${encodeURIComponent(state.search)}`;
        if (state.gender && state.gender !== "ALL") url += `&gender=${encodeURIComponent(state.gender)}`;
        if (state.quotas.length > 0) {
            state.quotas.forEach(q => url += `&quota=${encodeURIComponent(q)}`);
        }
        url += `&min_opening=${state.minOpening}&max_opening=${state.maxOpening}`;
        url += `&min_closing=${state.minClosing}&max_closing=${state.maxClosing}`;
        
        // Custom Entrance Rank filters
        url += `&mains_min=${state.mainsMin}&mains_max=${state.mainsMax}`;
        url += `&adv_min=${state.advMin}&adv_max=${state.advMax}`;
        url += `&filter_mains=${state.chkFilterMains}&filter_adv=${state.chkFilterAdv}`;
        url += `&user_mains_rank=${state.rankMains || 0}&user_adv_rank=${state.rankAdv || 0}`;
        
        const res = await fetch(url);
        const data = await res.json();
        
        if (!data.ranks || data.ranks.length === 0) {
            alert("No records to export.");
            return;
        }
        
        // CSV header
        let csvContent = "Institute,Academic Program Name,Quota,Seat Type,Gender,Opening 2025,Closing 2025,Ratio,Closing 2024,Closing 2023,Closing 2022\n";
        
        data.ranks.forEach(r => {
            const line = [
                `"${r.institute.replace(/"/g, '""')}"`,
                `"${r.program.replace(/"/g, '""')}"`,
                `"${r.quota}"`,
                `"${r.seat_type}"`,
                `"${r.gender}"`,
                r.opening_2025_str || "N/A",
                r.closing_2025_str || "N/A",
                r.standardized_ratio ? `${r.standardized_ratio.toFixed(2)}x` : "N/A",
                r.closing_2024_str || "N/A",
                r.closing_2023_str || "N/A",
                r.closing_2022_str || "N/A"
            ].join(",");
            csvContent += line + "\n";
        });
        
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement("a");
        const csvUrl = URL.createObjectURL(blob);
        
        link.setAttribute("href", csvUrl);
        link.setAttribute("download", `josaa_ranks_all_years_r${state.round}_${state.seatType}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
    } catch (e) {
        console.error("Failed to export CSV:", e);
    }
}

// Loading indicators
function showLoading(show) {
    if (show) {
        els.tableLoadingOverlay.classList.remove('d-none');
    } else {
        els.tableLoadingOverlay.classList.add('d-none');
    }
}

function showTableLoading(show) {
    if (show) {
        els.tableLoadingOverlay.classList.remove('d-none');
    } else {
        els.tableLoadingOverlay.classList.add('d-none');
    }
}

function updateProfileDisplay() {
    els.rankMainsDisplay.textContent = state.rankMains ? state.rankMains.toLocaleString('en-IN') : "Not Set";
    els.rankAdvDisplay.textContent = state.rankAdv ? state.rankAdv.toLocaleString('en-IN') : "Not Set";
    els.homeStateDisplay.textContent = (state.homeState && state.homeState !== "ALL") ? state.homeState : "All States";
}

function showProfileModal(firstTime = false) {
    els.modalRankMains.value = state.rankMains || "";
    els.modalRankAdv.value = state.rankAdv || "";
    els.modalSelectHomeState.value = state.homeState || "ALL";
    
    if (firstTime) {
        els.btnCancelProfile.textContent = "Skip";
    } else {
        els.btnCancelProfile.textContent = "Cancel";
    }
    
    els.profileModal.classList.remove('d-none');
}

function saveProfile() {
    const mainsVal = parseInt(els.modalRankMains.value) || 0;
    const advVal = parseInt(els.modalRankAdv.value) || 0;
    const homeStateVal = els.modalSelectHomeState.value || "ALL";
    
    state.rankMains = mainsVal;
    state.rankAdv = advVal;
    state.homeState = homeStateVal;
    
    localStorage.setItem('rankMains', mainsVal);
    localStorage.setItem('rankAdv', advVal);
    localStorage.setItem('homeState', homeStateVal);
    localStorage.setItem('profileSet_v3', 'true');
    
    updateClosingRankRangeFromMains();
    updateClosingRankRangeFromAdv();
    
    updateProfileDisplay();
    els.profileModal.classList.add('d-none');
    
    state.page = 1;
    fetchRanks();
}

function cancelProfile() {
    localStorage.setItem('profileSet_v3', 'true');
    els.profileModal.classList.add('d-none');
}

// Light / Dark Theme switching
function setupTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
    
    // Check if it's the first time app is started to prompt user and reset data
    const isFirstTime = !localStorage.getItem('profileSet_v3');
    if (isFirstTime) {
        localStorage.removeItem('rankMains');
        localStorage.removeItem('rankAdv');
        localStorage.removeItem('homeState');
        localStorage.removeItem('chkFilterMains');
        localStorage.removeItem('chkFilterAdv');
        localStorage.removeItem('mainsMin');
        localStorage.removeItem('advMin');
        state.rankMains = 0;
        state.rankAdv = 0;
        state.homeState = "ALL";
        state.chkFilterMains = false;
        state.chkFilterAdv = false;
    } else {
        // Load saved entrance ranks profile
        state.rankMains = parseInt(localStorage.getItem('rankMains')) || 0;
        state.rankAdv = parseInt(localStorage.getItem('rankAdv')) || 0;
        state.homeState = localStorage.getItem('homeState') || "ALL";
        state.chkFilterMains = localStorage.getItem('chkFilterMains') === 'true';
        state.chkFilterAdv = localStorage.getItem('chkFilterAdv') === 'true';
    }

    els.chkFilterMains.checked = state.chkFilterMains;
    els.chkFilterAdv.checked = state.chkFilterAdv;

    state.mainsMin = parseInt(localStorage.getItem('mainsMin')) || (state.rankMains ? Math.round(state.rankMains * 0.9) : 1);
    state.advMin = parseInt(localStorage.getItem('advMin')) || (state.rankAdv ? Math.round(state.rankAdv * 0.9) : 1);

    els.inputMainsMin.value = state.rankMains ? state.mainsMin : "";
    els.inputAdvMin.value = state.rankAdv ? state.advMin : "";

    document.getElementById('mains-range-display').style.display = state.chkFilterMains ? 'block' : 'none';
    document.getElementById('adv-range-display').style.display = state.chkFilterAdv ? 'block' : 'none';

    updateProfileDisplay();

    if (isFirstTime) {
        setTimeout(() => {
            showProfileModal(true);
        }, 100);
    }
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const icon = els.btnToggleTheme.querySelector('i');
    if (theme === 'dark') {
        icon.className = 'fa-solid fa-sun';
    } else {
        icon.className = 'fa-solid fa-moon';
    }
}

// ==========================================================================
// NEW COURSES EXPLORER TAB LOGIC
// ==========================================================================

let newCoursesData = [];
let newCoursesState = {
    search: "",
    instType: "ALL",
    quota: "ALL",
    gender: "Gender-Neutral",
    year: "2026",
    sortBy: "institute",
    sortDesc: false
};

function setupTabs() {
    const tabButtons = document.querySelectorAll('.nav-tab');
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.dataset.tab;
            state.activeTab = targetTab;
            
            // Toggle active classes on tab buttons
            tabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Toggle active classes on tab contents
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`tab-content-${targetTab}`).classList.add('active');
            
            // Show only the filters applicable for the current tab
            const rankingsFilters = document.getElementById('rankings-sidebar-filters');
            const newCoursesFilters = document.getElementById('new-courses-sidebar-filters');
            
            if (targetTab === 'new-courses') {
                if (rankingsFilters) rankingsFilters.style.display = 'none';
                if (newCoursesFilters) newCoursesFilters.style.display = 'block';
                
                // Sync UI controls with the current state
                const searchEl = document.getElementById('new-courses-sidebar-search');
                if (searchEl) searchEl.value = newCoursesState.search;
                
                const instTypeEl = document.getElementById('new-courses-sidebar-filter-inst-type');
                if (instTypeEl) instTypeEl.value = newCoursesState.instType;
                
                const quotaEl = document.getElementById('new-courses-sidebar-filter-quota');
                if (quotaEl) quotaEl.value = newCoursesState.quota;
                
                const genderEl = document.getElementById('new-courses-sidebar-filter-gender');
                if (genderEl) genderEl.value = newCoursesState.gender;
                
                const yearEl = document.getElementById('new-courses-sidebar-filter-year');
                if (yearEl) yearEl.value = newCoursesState.year;

                if (newCoursesData.length === 0) {
                    fetchNewCourses();
                } else {
                    renderNewCoursesTable();
                }
            } else {
                if (rankingsFilters) rankingsFilters.style.display = 'block';
                if (newCoursesFilters) newCoursesFilters.style.display = 'none';
            }
        });
    });
    
    // Add separate filter listeners for new courses (using the sidebar IDs)
    const newCoursesSearchInput = document.getElementById('new-courses-sidebar-search');
    if (newCoursesSearchInput) {
        newCoursesSearchInput.addEventListener('input', debounce((e) => {
            newCoursesState.search = e.target.value;
            renderNewCoursesTable();
        }, 250));
    }
    
    const newCoursesFilterInstType = document.getElementById('new-courses-sidebar-filter-inst-type');
    if (newCoursesFilterInstType) {
        newCoursesFilterInstType.addEventListener('change', (e) => {
            newCoursesState.instType = e.target.value;
            renderNewCoursesTable();
        });
    }
    
    const newCoursesFilterQuota = document.getElementById('new-courses-sidebar-filter-quota');
    if (newCoursesFilterQuota) {
        newCoursesFilterQuota.addEventListener('change', (e) => {
            newCoursesState.quota = e.target.value;
            renderNewCoursesTable();
        });
    }
    
    const newCoursesFilterGender = document.getElementById('new-courses-sidebar-filter-gender');
    if (newCoursesFilterGender) {
        newCoursesFilterGender.addEventListener('change', (e) => {
            newCoursesState.gender = e.target.value;
            renderNewCoursesTable();
        });
    }

    const newCoursesFilterYear = document.getElementById('new-courses-sidebar-filter-year');
    if (newCoursesFilterYear) {
        newCoursesFilterYear.addEventListener('change', (e) => {
            newCoursesState.year = e.target.value;
            renderNewCoursesTable();
        });
    }

    // Attach sorting listeners for new courses columns
    document.querySelectorAll('th.new-courses-sortable').forEach(th => {
        th.addEventListener('click', () => {
            const field = th.dataset.sort;
            if (newCoursesState.sortBy === field) {
                newCoursesState.sortDesc = !newCoursesState.sortDesc;
            } else {
                newCoursesState.sortBy = field;
                newCoursesState.sortDesc = false;
            }
            
            // Update sort icon UI inside new courses headers
            document.querySelectorAll('th.new-courses-sortable').forEach(header => {
                header.querySelector('i').className = 'fa-solid fa-sort';
            });
            const icon = th.querySelector('i');
            icon.className = newCoursesState.sortDesc ? 'fa-solid fa-sort-down' : 'fa-solid fa-sort-up';
            
            renderNewCoursesTable();
        });
    });
}

async function fetchNewCourses() {
    const loadingOverlay = document.getElementById('new-courses-loading-overlay');
    if (loadingOverlay) loadingOverlay.classList.remove('d-none');
    
    try {
        const res = await fetch('/api/new-courses');
        const data = await res.json();
        newCoursesData = data.new_courses || [];
        
        // Populate new courses Quota dropdown dynamically based on non-baseline new courses
        const quotaSelect = document.getElementById('new-courses-sidebar-filter-quota');
        if (quotaSelect) {
            // Find active non-baseline new courses (start_year > 2022)
            const activeNewCourses = newCoursesData.filter(c => c.start_year > 2022);
            // Find unique quotas (filtering out N/A and empty values)
            const uniqueQuotas = [...new Set(activeNewCourses.map(c => c.quota))].filter(q => q && q !== "N/A" && q.trim() !== "").sort();
            quotaSelect.innerHTML = '<option value="ALL" selected>All Quotas</option>';
            uniqueQuotas.forEach(q => {
                const opt = document.createElement('option');
                opt.value = q;
                opt.textContent = q;
                quotaSelect.appendChild(opt);
            });
            // Ensure selected option matches current state
            quotaSelect.value = newCoursesState.quota;
        }
        
        renderNewCoursesTable();
    } catch (e) {
        console.error("Error fetching new courses:", e);
    } finally {
        if (loadingOverlay) loadingOverlay.classList.add('d-none');
    }
}

function renderNewCoursesTable() {
    const tbody = document.getElementById('new-courses-tbody');
    const emptyState = document.getElementById('new-courses-empty-state');
    const countSpan = document.getElementById('new-courses-count');
    
    tbody.innerHTML = "";
    
    // Filter courses based on newCoursesState
    let filtered = newCoursesData.filter(c => {
        // Exclude baseline courses that existed since the start of JoSAA (start_year <= 2022)
        if (c.start_year <= 2022) return false;

        // Search filter
        const query = (newCoursesState.search || "").toLowerCase();
        const matchesSearch = c.institute.toLowerCase().includes(query) || c.program.toLowerCase().includes(query);
        
        // Quota filter
        const matchesQuota = newCoursesState.quota === "ALL" || c.quota === newCoursesState.quota;
        
        // Gender/Seat Pool filter
        const matchesGender = newCoursesState.gender === "ALL" || c.seat_pool === newCoursesState.gender;
        
        // Institute Type filter
        const matchesInstType = newCoursesState.instType === "ALL" || getInstituteType(c.institute) === newCoursesState.instType;
        
        // Introduction Year filter
        let matchesYear = true;
        if (newCoursesState.year !== "ALL") {
            matchesYear = parseInt(c.start_year) === parseInt(newCoursesState.year);
        }
        
        return matchesSearch && matchesQuota && matchesGender && matchesInstType && matchesYear;
    });

    // Client-side sorting implementation for new courses
    const field = newCoursesState.sortBy || "institute";
    const order = newCoursesState.sortDesc ? -1 : 1;
    filtered.sort((a, b) => {
        let valA = a[field];
        let valB = b[field];
        
        if (typeof valA === 'string') {
            return valA.localeCompare(valB) * order;
        }
        if (typeof valA === 'number') {
            return (valA - valB) * order;
        }
        return 0;
    });
    
    // Dynamically update stats block based on FILTERED results
    const activeFiltered = filtered.filter(c => c.is_active);
    document.getElementById('stat-new-courses-count').textContent = activeFiltered.length;
    
    let totalSeats = 0;
    activeFiltered.forEach(c => totalSeats += (c.total || 0));
    document.getElementById('stat-new-courses-seats').textContent = totalSeats.toLocaleString('en-IN');
    
    countSpan.textContent = `Showing ${filtered.length} courses`;
    
    if (filtered.length === 0) {
        emptyState.classList.remove('d-none');
        return;
    }
    emptyState.classList.add('d-none');
    
    filtered.forEach((c, idx) => {
        const row = document.createElement('tr');
        
        // Build badges
        const statusBadge = c.is_active 
            ? '' 
            : `<span class="badge badge-danger" style="font-size: 10px; margin-left: 6px; padding: 2px 6px; font-weight: 600; border-radius: 4px; background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.25);">Discontinued / Inactive</span>`;
            
        row.innerHTML = `
            <td>${c.institute}${statusBadge}</td>
            <td>${c.program}</td>
            <td><strong>${c.start_year}</strong></td>
            <td><span class="badge badge-outline">${c.quota}</span></td>
            <td>${c.seat_pool}</td>
            <td><strong>${c.is_active ? c.total : '-'}</strong></td>
            <td>
                <button class="btn-details" data-idx="${idx}"><i class="fa-solid fa-eye"></i> Details</button>
            </td>
        `;
        tbody.appendChild(row);
        
        // Detailed row (hidden by default)
        const detailRow = document.createElement('tr');
        detailRow.className = 'details-row d-none';
        detailRow.id = `detail-row-${idx}`;
        
        const detailsContainerHTML = c.is_active ? `
            <div class="details-container">
                <div style="display: flex; gap: 24px; font-size: 13px; color: var(--text-secondary); margin-bottom: 8px;">
                    <span><strong>Program Total Capacity:</strong> ${c.program_total}</span>
                    <span><strong>Female Supernumerary Seats:</strong> ${c.female_supernumerary}</span>
                </div>
                <strong>Seat Category Distribution Breakdown:</strong>
                <div class="breakdown-grid">
                    ${Object.entries(c.seats).map(([cat, val]) => `
                        <div class="breakdown-item">
                            <div class="breakdown-label">${cat.replace('_', '-')}</div>
                            <div class="breakdown-value">${val}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        ` : `
            <div class="details-container">
                <div style="font-size: 13px; color: var(--text-secondary);">
                    This program has been discontinued or is inactive for the current academic year seat matrix. Historical statistics cannot be queried.
                </div>
            </div>
        `;
        
        detailRow.innerHTML = `
            <td colspan="7">
                ${detailsContainerHTML}
            </td>
        `;
        tbody.appendChild(detailRow);
    });
    
    // Attach details button event listeners
    tbody.querySelectorAll('.btn-details').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const idx = btn.dataset.idx;
            const targetDetail = document.getElementById(`detail-row-${idx}`);
            if (targetDetail.classList.contains('d-none')) {
                targetDetail.classList.remove('d-none');
                btn.innerHTML = `<i class="fa-solid fa-eye-slash"></i> Hide`;
            } else {
                targetDetail.classList.add('d-none');
                btn.innerHTML = `<i class="fa-solid fa-eye"></i> Details`;
            }
        });
    });
}



