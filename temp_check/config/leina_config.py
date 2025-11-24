# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any

LEINA_DEFAULTS: Dict[str, Any] = {
    # Personality settings
    "LEINA_CATCHPHRASE_RATE": 0.3,      # Frequensi catchphrase
    "LEINA_GLITCH_CHANCE": 0.1,         # Kemungkinan glitch
    "LEINA_CAT_MODE": True,             # Mode kucing aktif
    "LEINA_STREAM_AWARE": True,         # Aware dengan stream
    
    # Interaction settings
    "LEINA_HEADPAT_COOLDOWN": 60,       # Cooldown headpat dalam detik
    "LEINA_REACTION_CHANCE": 0.4,       # Kemungkinan reaksi emoji
    "LEINA_MEMORY_RECALL_SIZE": 5,      # Jumlah memori yang di-recall
    
    # Mood settings
    "LEINA_DEFAULT_MOOD": "happy",      # Mood default
    "LEINA_MOOD_CHANGE_CHANCE": 0.2,    # Kemungkinan pergantian mood
    
    # Stream integration
    "LEINA_STREAM_CHECK_INTERVAL": 300,  # Interval cek stream (5 menit)
    "LEINA_STREAM_ANNOUNCE": True,       # Pengumuman stream
}