#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import glob

# ===============================================================
# Lettura Dati
# ===============================================================
print("[INFO] Caricando dati")
lqr_files = glob.glob('../data/lqr_log_*.csv')
if not lqr_files:
    print("[ERRORE] Nessun file lqr_log_*.csv trovato!")
    exit(1)
lqr_file = sorted(lqr_files)[-1]
df_lqr = pd.read_csv(lqr_file)
print(
    f"    NUMERO CAMPIONI: {len(df_lqr)}\n" 
    f"    DATASET: {lqr_file}")

load_files = glob.glob('../data/load_log_*.csv')
df_load = None
if load_files:
    load_file = sorted(load_files)[-1]
    df_load = pd.read_csv(load_file)
    print(f"    LOAD DATASET: {load_file}")
else:
    print("[WARN] Nessun file load_log_*.csv trovato, grafico traffico saltato.")

# ===============================================================
# CALCOLA METRICHE
# ===============================================================
def compute_metrics(df):
    x_max      = df['x'].max()
    suffering  = df['suffering'].sum() if 'suffering' in df.columns else 0.0
    scale_events = (df['x'].diff().abs() > 0).sum()
    return dict(
        x_max=x_max, x_mean=df['x'].mean(), suffering=suffering, scale_events=scale_events)

m = compute_metrics(df_lqr)
fmt = lambda v, dec=1, unit="": f"{v:.{dec}f}{unit}" if v is not None else "N/A"

# ===============================================================
# GRAFICO 1
# ===============================================================
n_plots = 4 if df_load is not None else 3
fig = plt.figure(figsize=(14, 5 * n_plots))
fig.patch.set_facecolor('#FAFAFA')
fig.suptitle('Analisi LQR Autoscaler', fontsize=15, fontweight='bold', y=0.99)

gs = gridspec.GridSpec(n_plots, 1, figure=fig,
                       hspace=0.50,
                       left=0.08, right=0.97,
                       top=0.95, bottom=0.04)

COLOR_LQR  = '#D85A30'
COLOR_LOAD = '#2980B9'
GRID_KW    = dict(alpha=0.25, linestyle='--')

# ===================== GRAFICO REPLICHE ===========================================================================
ax1 = fig.add_subplot(gs[0])
ax1.plot(
    df_lqr['t'], df_lqr['x'], label='Repliche (x)', color=COLOR_LQR, lw=2.2, marker='s', markersize=3, alpha=0.85)
ax1.plot(
    df_lqr['t'], df_lqr['x_ref'], label='Riferimento (x_ref)', color='gray', lw=1.5, linestyle='--', alpha=0.7)

ax1.set_xlabel('Tempo [s]'); ax1.set_ylabel('Repliche')
ax1.set_title('Scaling dinamico', fontweight='bold')
ax1.legend(fontsize=9); ax1.grid(**GRID_KW); ax1.set_ylim(bottom=0)

# ===================== GRAFICO LATENZA ===========================================================================
ax2 = fig.add_subplot(gs[1])
ax2.plot(df_lqr['t'], df_lqr['l'], label='Latenza misurata',
         color=COLOR_LQR, lw=2.2, alpha=0.85)
ax2.axhline(0.4, color='green', lw=1.5, linestyle='--', label='L_ref = 0.4s')
ax2.fill_between(df_lqr['t'], df_lqr['l'], 0.4,
                 where=df_lqr['l'] > 0.4, alpha=0.2, color=COLOR_LQR, label='Violazione SLA')
ax2.set_xlabel('Tempo [s]'); ax2.set_ylabel('Latenza [s]')
ax2.set_title('Latenza nel tempo', fontweight='bold')
ax2.legend(fontsize=9); ax2.grid(**GRID_KW); ax2.set_ylim(bottom=0)

# ===================== GRAFICO LATENZA CUMULATIVA =================================================================
ax3 = fig.add_subplot(gs[2])
if 'suffering' in df_lqr.columns and df_lqr['suffering'].sum() > 0:
    ax3.fill_between(df_lqr['t'], df_lqr['suffering'], 0,
                     alpha=0.25, color=COLOR_LQR)
    ax3.plot(df_lqr['t'], df_lqr['suffering'],
             color=COLOR_LQR, lw=2.2, label='z (sofferenza)')
ax3.axhline(0, color='black', lw=0.8)
ax3.set_xlabel('Tempo [s]'); ax3.set_ylabel('Sofferenza [req/s]')
ax3.set_title('Sofferenza cumulativa nel tempo', fontweight='bold')
ax3.legend(fontsize=9); ax3.grid(**GRID_KW); ax3.set_ylim(bottom=0)

# ===================== GRAFICO TRAFFICO ===========================================================================
if df_load is not None:
    ax4 = fig.add_subplot(gs[3])

    # request rate: conta richieste per bin di 1s
    t_max  = df_load['t'].max()
    bins   = np.arange(0, t_max + 1, 1.0)
    counts, edges = np.histogram(df_load['t'], bins=bins)
    bin_centers = (edges[:-1] + edges[1:]) / 2

    ax4.plot(bin_centers, counts, color=COLOR_LOAD, lw=2.2, alpha=0.85, label='Req/s (totale)')
    ax4.fill_between(bin_centers, counts, alpha=0.15, color=COLOR_LOAD)

    # overlay errori (status != 200)
    if 'status' in df_load.columns:
        df_err = df_load[df_load['status'] != 200]
        if not df_err.empty:
            err_counts, _ = np.histogram(df_err['t'], bins=bins)
            ax4.plot(bin_centers, err_counts, color='#E74C3C', lw=1.8, alpha=0.85, label='Req/s (errori)')
            ax4.fill_between(bin_centers, err_counts, alpha=0.2, color='#E74C3C')

    ax4.set_xlabel('Tempo [s]'); ax4.set_ylabel('Richieste [req/s]')
    ax4.set_title('Profilo di traffico generato', fontweight='bold')
    ax4.legend(fontsize=9); ax4.grid(**GRID_KW); ax4.set_ylim(bottom=0)

# ===============================================================
# TABELLA
# ===============================================================
rows = [
    ['Max Repliche',                 fmt(m['x_max'], 0)],
    ['Repliche Medie',               fmt(m['x_mean'], 2)],
    ['Sofferenza cumulativa',        fmt(m['suffering'])],
    ['Scaling Events',               fmt(m['scale_events'], 0)],
]

col_labels = ['Metrica', 'LQR']
fig_tbl, ax_tbl = plt.subplots(figsize=(8, 3.2))
fig_tbl.patch.set_facecolor('#FAFAFA')
ax_tbl.axis('off')
tbl = ax_tbl.table(cellText=rows, colLabels=col_labels, loc='center', cellLoc='center')
tbl.auto_set_font_size(False); tbl.set_fontsize(10); tbl.scale(1, 1.7)
for j in range(len(col_labels)):
    tbl[0, j].set_facecolor('#2C3E50')
    tbl[0, j].set_text_props(color='white', fontweight='bold')
for i in range(1, len(rows) + 1):
    tbl[i, 0].set_facecolor('#EEF2F7')
    tbl[i, 1].set_facecolor('#FDF0EB')
ax_tbl.set_title('Riepilogo performance LQR', fontweight='bold', pad=8)

fig.savefig('analisi_lqr.png',       dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
fig_tbl.savefig('tabella_lqr.png',   dpi=150, bbox_inches='tight', facecolor=fig_tbl.get_facecolor())
print("[PLOT] Salvati: analisi_lqr.png, tabella_lqr.png")
plt.show()