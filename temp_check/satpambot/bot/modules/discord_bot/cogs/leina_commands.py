# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import time
import random
import asyncio
import logging
from typing import Dict, Any, Optional

import discord
from discord.ext import commands
from discord import app_commands

from ..helpers.leina.personality import LeinaPersonality
from ..helpers.leina.memory import LeinaMemoryDB, Memory
# config runtime import intentionally omitted to avoid unused import

# Import AI clients conditionally
try:
    from groq import Groq
    has_groq = True
except ImportError:
    has_groq = False
    Groq = None

# Gemini (Google generative AI) is not initialized here to avoid import/time issues
has_gemini = False
genai = None

log = logging.getLogger(__name__)

class LeinaCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.personality = LeinaPersonality()
        self.memory_db = LeinaMemoryDB()
        self.last_headpat: Dict[int, float] = {}
        
        # Initialize AI clients
        self.groq_client: Optional[Any] = None
        self.gemini_client: Optional[Any] = None
        
        if has_groq and Groq is not None and os.getenv("GROQ_API_KEY"):
            self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        # Gemini client initialization skipped in this environment (optional at runtime)
        self.gemini_client = None

    async def _get_ai_response(self, prompt: str, system_prompt: str = "") -> str:
        """Get response from available AI providers"""
        try:
            if self.groq_client is not None:
                try:
                    chat_completion = await asyncio.to_thread(
                        self.groq_client.chat.completions.create,
                        model="mixtral-8x7b-32768",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=150
                    )
                    content = chat_completion.choices[0].message.content
                    return content if content is not None else "Error: No content generated"
                except Exception as e:
                    log.error(f"Groq API error: {e}")
                    raise
            
            if self.gemini_client is not None:
                try:
                    response = await asyncio.to_thread(
                        self.gemini_client.generate_content,
                        prompt
                    )
                    return str(response.text)
                except Exception as e:
                    log.error(f"Gemini API error: {e}")
                    raise
                
            return "Processing error... No AI provider available *sad beep*"
        except Exception as e:
            log.error(f"AI response error: {e}")
            return "My circuits are having trouble processing... *confused whir*"

    @app_commands.command(name="compute")
    async def compute(self, interaction: discord.Interaction, expression: str):
        """Leina will compute mathematical expressions"""
        try:
            # Define safe math operations
            safe_dict: Dict[str, Any] = {
                'abs': abs,
                'round': round,
                'min': min,
                'max': max,
                'pow': pow,
                'sum': sum
            }
            
            # Create a restricted environment for evaluation
            restricted_globals: Dict[str, Dict[str, Any]] = {"__builtins__": {}}
            
            # Evaluate expression and ensure numeric result
            raw_result = eval(expression, restricted_globals, safe_dict)
            result = float(raw_result)
            
            response = self.personality.format_message(
                f"Processing complete! {expression} = {result}",
                mood="happy"
            )
        except Exception as e:
            log.warning(f"Compute error for expression '{expression}': {e}")
            response = self.personality.format_message(
                "*circuit overload* Could not compute that expression...",
                mood="confused"
            )
        await interaction.response.send_message(response)

    @app_commands.command(name="chat")
    @app_commands.describe(message="What would you like to say to Leina?")
    async def chat(self, interaction: discord.Interaction, message: str):
        """Chat with Leina"""
        await interaction.response.defer()
        
        from ..helpers.leina.prompts import LEINA_SYSTEM_PROMPT
        response = await self._get_ai_response(message, LEINA_SYSTEM_PROMPT)
        
        # Store interaction in memory
        await self.memory_db.add_memory(Memory(
            category="master_interactions" if interaction.user.id == int(os.getenv("OWNER_USER_ID", "0"))
                    else "user_interactions",
            content=f"{interaction.user.name}: {message}",
            timestamp=time.time(),
            importance=2 if "master" in message.lower() else 1
        ))
        
        await interaction.followup.send(
            self.personality.format_message(response)
        )

    @app_commands.command(name="headpat")
    async def headpat(self, interaction: discord.Interaction):
        """Give Leina a headpat!"""
        user_id = interaction.user.id
        now = time.time()
        cooldown = 60  # 1 minute cooldown

        if user_id in self.last_headpat and (now - self.last_headpat[user_id]) < cooldown:
            remaining = int(cooldown - (now - self.last_headpat[user_id]))
            await interaction.response.send_message(
                self.personality.format_message(
                    f"*processor purring* Please wait {remaining}s for my sensors to reset!",
                    mood="playful"
                )
            )
            return

        self.last_headpat[user_id] = now
        
        # Store headpat in memory
        await self.memory_db.add_memory(Memory(
            category="user_favorites",
            content=f"Received headpat from {interaction.user.name}",
            timestamp=now,
            importance=1
        ))
        
        await interaction.response.send_message(
            self.personality.get_response("thanks", "*happy system noises* Headpats detected!")
        )

    @app_commands.command(name="glitch")
    async def glitch(self, interaction: discord.Interaction, intensity: app_commands.Range[int, 1, 3] = 1):
        """Membuat Leina 'glitch' dengan intensitas tertentu"""
        glitch_levels = {
            1: ["*minor glitch*", "*system hiccup*", "*brief static*"],
            2: ["*visible pixelation*", "*reality buffer overflow*", "*matrix fluctuation*"],
            3: ["*CRITICAL_PROCESS_ERROR*", "*reality.exe has stopped working*", "*emergency reboot required*"]
        }
        
        response = random.choice(glitch_levels[intensity])
        await interaction.response.send_message(
            self.personality.format_message(response, mood="confused")
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(LeinaCommands(bot))