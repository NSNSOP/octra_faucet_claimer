#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script automasi untuk melakukan klaim faucet dari Octra Network secara massal.
Fitur termasuk pemilihan wallet interaktif, penanganan coba lagi (retry) yang cerdas,
pembersihan cache otomatis, laporan hasil akurat, dan fitur untuk mengulang wallet gagal.
"""

import functools
import os
import shutil
import sys
import time
from typing import List, Optional, Tuple

import questionary
import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# ==============================================================================
# --- PUSAT KONFIGURASI ---
# ==============================================================================
class Config:
    """Menyimpan semua variabel konfigurasi."""
    SOLVER_API_KEY: str = "ISI_API_KEY_ANDA_DI_SINI"
    WALLETS_DIR: str = "wallets"
    SOLVER_IN_URL: str = "https://api.solvecaptcha.com/in.php"
    SOLVER_RES_URL: str = "https://api.solvecaptcha.com/res.php"
    FAUCET_CLAIM_URL: str = "https://faucet.octra.network/claim"
    FAUCET_PAGE_URL: str = "https://faucet.octra.network/"
    FAUCET_SITEKEY: str = "6LekoXkrAAAAAMlLCpc2KJqSeUHye6KMxOL5_SES"
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: int = 5
    WALLET_DELAY_SECONDS: int = 10

console = Console()

def clean_project_cache():
    """Mencari dan menghapus folder __pycache__ serta memberikan konfirmasi."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cache_dir = os.path.join(script_dir, '__pycache__')
        if os.path.isdir(cache_dir):
            shutil.rmtree(cache_dir)
            console.print(f"   [bold yellow]🧹 Cache proyek ([italic]__pycache__[/italic]) telah dibersihkan.[/bold yellow]")
        else:
            console.print(f"   [bold green]✓ Cache proyek sudah bersih (tidak ditemukan).[/bold green]")
    except Exception as e:
        console.print(f"   [yellow]Peringatan: Gagal memproses cache proyek. Error: {e}[/yellow]")

def retry_handler(max_retries: int, delay: int):
    """Decorator cerdas untuk menangani coba lagi pada sebuah fungsi."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                if attempt > 0:
                    console.print(f"\n   --- [ Mencoba Lagi - Percobaan {attempt + 1}/{max_retries} ] ---")
                try:
                    success = func(*args, **kwargs)
                    if success: return True
                except requests.exceptions.RequestException as e:
                    console.print(f"   [yellow]Error Koneksi: {e}[/yellow]")
                if attempt < max_retries - 1:
                    console.print(f"   [cyan]Proses akan diulang dalam {delay} detik...[/cyan]")
                    time.sleep(delay)
            console.print(f"   [bold red]✗ Gagal permanen untuk wallet ini setelah {max_retries} percobaan.[/bold red]")
            return False
        return wrapper
    return decorator

def parse_selection_range(selection_str: str, max_val: int) -> List[int]:
    """Mengubah string input menjadi daftar indeks unik (berbasis 0)."""
    indices = set()
    parts = selection_str.split(',')
    for part in parts:
        part = part.strip()
        if not part: continue
        try:
            if '-' in part:
                start, end = map(int, part.split('-')); start, end = (start, end) if start <= end else (end, start)
                for i in range(start, end + 1):
                    if 1 <= i <= max_val: indices.add(i - 1)
            else:
                num = int(part)
                if 1 <= num <= max_val: indices.add(num - 1)
        except ValueError:
            console.print(f"[yellow]Peringatan: Input '{part}' tidak valid dan akan diabaikan.[/yellow]")
    return sorted(list(indices))

def get_wallet_address_from_file(filepath: str) -> Optional[str]:
    """Membaca file wallet dan mengambil alamatnya."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith("Address:"):
                    return line.split("Address:")[1].strip()
    except Exception as e:
        console.print(f"[red]Error saat membaca {os.path.basename(filepath)}: {e}[/red]")
    return None

def get_captcha_token() -> Optional[str]:
    """Menghubungi API solver untuk mendapatkan token reCAPTCHA."""
    console.print("   [cyan]1. Meminta token CAPTCHA baru...[/cyan]")
    payload = {'key': Config.SOLVER_API_KEY, 'method': 'userrecaptcha', 'googlekey': Config.FAUCET_SITEKEY, 'pageurl': Config.FAUCET_PAGE_URL, 'json': 1}
    response = requests.post(Config.SOLVER_IN_URL, data=payload, timeout=30); response.raise_for_status()
    response_data = response.json()
    if response_data.get('status') != 1:
        console.print(f"   [red]Solver Gagal: {response_data.get('request')}[/red]"); return None
    request_id = response_data.get('request')
    params = {'key': Config.SOLVER_API_KEY, 'action': 'get', 'id': request_id, 'json': 1}
    with console.status(f"[bold green]Menunggu hasil CAPTCHA...[/bold green]"):
        end_time = time.time() + 180
        while time.time() < end_time:
            time.sleep(5)
            res_response = requests.get(Config.SOLVER_RES_URL, params=params, timeout=30); res_response.raise_for_status()
            res_data = res_response.json()
            if res_data.get('status') == 1:
                console.print("   [green]✓ CAPTCHA berhasil didapatkan![/green]"); return res_data.get('request')
            if res_data.get('request') != 'CAPCHA_NOT_READY':
                console.print(f"\n   [red]Solver Gagal: {res_data.get('request')}[/red]"); return None
    console.print(f"\n   [red]Solver Gagal (timeout 3 menit).[/red]"); return None

def claim_faucet(wallet_address: str, captcha_token: str) -> bool:
    """Mengirim permintaan klaim ke server faucet."""
    console.print(f"   [cyan]2. Melakukan klaim untuk:[/cyan] [yellow]{wallet_address[:15]}...{wallet_address[-4:]}[/yellow]")
    form_data = {'address': (None, wallet_address), 'is_validator': (None, 'false'), 'g-recaptcha-response': (None, captcha_token)}
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.post(Config.FAUCET_CLAIM_URL, files=form_data, headers=headers, timeout=30); response.raise_for_status()
    try:
        response_data = response.json()
        if response_data.get("success"):
            console.print(f"   [bold green]✓ Berhasil![/bold green] Amount: [bold yellow]{response_data.get('amount')}[/bold yellow], Tx: [bold cyan]{response_data.get('tx_hash')[:20]}...[/bold cyan]")
            return True
        else:
            error_msg = response_data.get('error', 'Pesan error tidak diketahui')
            console.print(f"   [red]✗ Gagal:[/red] Server merespons dengan pesan: [italic]'{error_msg}'[/italic]")
            return False
    except ValueError:
        console.print(f"   [red]✗ Gagal:[/red] Respons server bukan format JSON yang valid.")
        return False

@retry_handler(max_retries=Config.MAX_RETRIES, delay=Config.RETRY_DELAY_SECONDS)
def process_single_wallet(address: str) -> bool:
    """Menggabungkan proses get_token dan claim. Fungsi inilah yang akan di-retry."""
    token = get_captcha_token()
    if not token: return False
    return claim_faucet(address, token)

def display_results_summary(successful_wallets: List[Tuple[int, str]], failed_wallets: List[Tuple[int, str]]):
    """Menampilkan panel ringkasan hasil akhir proses klaim."""
    total_processed = len(successful_wallets) + len(failed_wallets)
    summary_text = Text(justify="center")
    summary_text.append(f"Total Diproses: {total_processed}\n")
    summary_text.append("Berhasil: ", style="bold green"); summary_text.append(f"{len(successful_wallets)}\n")
    summary_text.append("Gagal: ", style="bold red"); summary_text.append(f"{len(failed_wallets)}")
    
    if failed_wallets:
        failed_table = Table(title="Daftar Wallet yang Gagal (Final)")
        failed_table.add_column("No. Asli", style="cyan", justify="right")
        failed_table.add_column("Nama File Wallet", style="red")
        for original_number, filename in failed_wallets:
            failed_table.add_row(str(original_number), filename)
        console.print(failed_table)

    console.print(Panel(summary_text, title="[bold yellow]📊 Laporan Hasil Akhir[/bold yellow]", border_style="blue"))

def run_claim_process(wallets_to_process: List[Tuple[int, str]]) -> Tuple[List[Tuple[int, str]], List[Tuple[int, str]]]:
    """
    Menjalankan proses klaim untuk daftar wallet yang diberikan.

    :param wallets_to_process: Daftar tuple (nomor_asli, nama_file) untuk diproses.
    :return: Tuple berisi (daftar_sukses, daftar_gagal).
    """
    successful_run = []
    failed_run = []
    
    for loop_count, (original_number, filename) in enumerate(wallets_to_process, 1):
        console.print(f"\n--- [ Memproses Wallet {loop_count}/{len(wallets_to_process)} (No. Asli: {original_number}): [bold]{filename}[/bold] ] ---")
        filepath = os.path.join(Config.WALLETS_DIR, filename)
        address = get_wallet_address_from_file(filepath)
        
        if not address:
            console.print(f"   [red]✗ Gagal mendapatkan alamat dari file.[/red]")
            failed_run.append((original_number, filename))
        else:
            was_successful = process_single_wallet(address)
            if was_successful:
                successful_run.append((original_number, filename))
            else:
                failed_run.append((original_number, filename))
        
        console.print("\n[bold]Memeriksa cache pasca-proses...[/bold]")
        clean_project_cache()
        if loop_count < len(wallets_to_process):
            console.print(f"\n[cyan]Jeda {Config.WALLET_DELAY_SECONDS} detik sebelum ke wallet berikutnya...[/cyan]"); time.sleep(Config.WALLET_DELAY_SECONDS)
    
    return successful_run, failed_run

def main():
    """Fungsi utama yang mengorkestrasi seluruh alur kerja skrip."""
    console.print(Panel.fit("[bold cyan]OCTRA Multi-Claim Faucet Script[/bold cyan]\n(v7.0 - Dengan Fitur Ulangi Gagal)", title="[yellow]Welcome[/yellow]"))
    console.print("\n[bold]Memulai dengan memeriksa cache awal...[/bold]")
    clean_project_cache()
    if not os.path.isdir(Config.WALLETS_DIR):
        console.print(f"[red]Error: Folder '{Config.WALLETS_DIR}' tidak ditemukan.[/red]"); sys.exit(1)
    
    wallet_files = sorted([f for f in os.listdir(Config.WALLETS_DIR) if f.endswith('.txt')])
    if not wallet_files:
        console.print(f"[yellow]Tidak ada file wallet (.txt) di folder '{Config.WALLETS_DIR}'.[/yellow]"); return
    
    table = Table(title="Daftar Wallet Tersedia"); table.add_column("No.", style="cyan", justify="right"); table.add_column("Nama File", style="magenta")
    for i, filename in enumerate(wallet_files, 1): table.add_row(str(i), filename)
    console.print(table)
    
    try:
        selection_str = questionary.text('Masukkan nomor wallet untuk diklaim:', instruction="(Contoh: 1, 3, 5-8 atau 'semua')").ask()
    except KeyboardInterrupt:
        console.print("\n[yellow]Proses dibatalkan oleh pengguna.[/yellow]"); return
    if not selection_str:
        console.print("[yellow]Tidak ada input. Keluar.[/yellow]"); return
    
    if selection_str.lower() == 'semua':
        selected_indices = list(range(len(wallet_files)))
    else:
        selected_indices = parse_selection_range(selection_str, len(wallet_files))
    if not selected_indices:
        console.print("[red]Pilihan tidak valid. Keluar.[/red]"); return
    
    # Membuat daftar awal wallet yang akan diproses
    wallets_to_process = [(idx + 1, wallet_files[idx]) for idx in selected_indices]
    
    all_successful_wallets = []
    
    # Loop utama: akan terus berjalan selama ada wallet yang gagal dan user ingin mengulang
    while wallets_to_process:
        console.print(Panel(f"[bold green]Akan memulai proses untuk {len(wallets_to_process)} wallet...[/bold green]"))
        
        successful_this_run, failed_this_run = run_claim_process(wallets_to_process)
        
        # Akumulasi hasil yang sukses
        all_successful_wallets.extend(successful_this_run)
        
        # Persiapan untuk iterasi berikutnya
        wallets_to_process = failed_this_run
        
        if wallets_to_process:
            console.print("\n" + "="*60 + "\n")
            console.print(f"[bold yellow]Proses Selesai, namun ditemukan {len(wallets_to_process)} wallet yang masih gagal.[/bold yellow]")
            try:
                wants_to_retry = questionary.confirm("Apakah Anda ingin mencoba menjalankan ulang wallet yang gagal?").ask()
                if not wants_to_retry:
                    break # Keluar dari loop jika user tidak ingin mengulang
            except KeyboardInterrupt:
                console.print("\n[yellow]Proses pengulangan dibatalkan.[/yellow]")
                break
        else:
            console.print("\n[bold green]🎉 Selamat! Semua wallet berhasil diproses![/bold green]")

    # Laporan akhir setelah loop selesai
    console.print("\n" + "="*60 + "\n")
    display_results_summary(all_successful_wallets, wallets_to_process)

if __name__ == "__main__":
    if Config.SOLVER_API_KEY == "API_KEY_ANDA" or not Config.SOLVER_API_KEY:
        console.print("[bold red]ERROR: Harap isi `SOLVER_API_KEY` di dalam 'Config' skrip terlebih dahulu![/bold red]")
    else:
        main()
