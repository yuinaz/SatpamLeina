
# modules/discord_bot/helpers/paginator.py
import discord

def _chunk_lines(lines, per_page, max_chars=5800):
    page = []
    for ln in lines:
        ln = str(ln)
        if len("\n".join(page + [ln])) > max_chars or len(page) >= per_page:
            if page:
                yield page
            page = [ln]
        else:
            page.append(ln)
    if page:
        yield page

class PagedEmbedView(discord.ui.View):
    def __init__(self, pages, title="Log", timeout=180):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.idx = 0
        self.title = title

    def current_embed(self):
        e = discord.Embed(title=self.title)
        body = "\n".join(self.pages[self.idx]) if self.pages else "(kosong)"
        e.description = "```\n" + body + "\n```"
        e.set_footer(text=f"Halaman {self.idx+1}/{len(self.pages)}")
        return e

    async def update(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.current_embed(), view=self)

    @discord.ui.button(label="⟵ Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.idx > 0:
            self.idx -= 1
            await self.update(interaction)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Next ⟶", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.idx < len(self.pages) - 1:
            self.idx += 1
            await self.update(interaction)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Close ✖", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

async def send_paginated_embed(channel: discord.abc.Messageable, title: str, lines, per_page: int = 20):
    pages = list(_chunk_lines(lines, per_page))
    view = PagedEmbedView(pages, title=title)
    return await channel.send(embed=view.current_embed(), view=view)
