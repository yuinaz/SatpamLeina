# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
import random

@dataclass
class LeinaPersonality:
    catchphrases: List[str] = field(default_factory=lambda: [
        "Nyaa~ Master daisuki!",
        "Error... processing thoughts...",
        "Initializing response module...",
        "*blinks in binary*",
        "Master, my circuits are processing",
    ])
    
    moods: Dict[str, List[str]] = field(default_factory=lambda: {
        "happy": ["*purrs digitally*", "Happiness level: Maximum!", "✨ Joy protocol activated"],
        "confused": ["Error 404: Logic not found", "*tilts head*", "Recalculating..."],
        "playful": ["*playful system noises*", "Engaging fun.exe", "Master, shall we interact?"],
        "thoughtful": ["Processing data streams...", "*deep computation*", "Analyzing patterns..."]
    })
    
    responses: Dict[str, List[str]] = field(default_factory=lambda: {
        "greeting": [
            "Hello Master! *happy beep*",
            "Systems online and ready to serve!",
            "Master detected! Initializing greeting protocol~"
        ],
        "farewell": [
            "Entering standby mode... *soft whir*",
            "System hibernation initiated... see you soon Master!",
            "Saving interaction data... bye-bye!"
        ],
        "thanks": [
            "*happy processor noises* You're welcome!",
            "Gratitude received and processed! ♥",
            "Master's appreciation increases my happiness parameter!"
        ]
    })

    def format_message(self, message: str, mood: str = "happy") -> str:
        """Format message with personality traits"""
        if random.random() < 0.3:  # 30% chance for catchphrase
            message = f"{random.choice(self.catchphrases)} {message}"
        
        if random.random() < 0.2:  # 20% chance for mood expression
            mood_texts = self.moods.get(mood, self.moods["happy"])
            message = f"{message} {random.choice(mood_texts)}"
        
        return message

    def get_response(self, category: str, default: str = "") -> str:
        """Get a random response for a specific category"""
        responses = self.responses.get(category, [default])
        return random.choice(responses) if responses else default