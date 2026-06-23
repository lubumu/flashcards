#!/usr/bin/env python3
"""
Flashcard learning application for Latin vocabulary (Adeamus).
Provides lesson selection, card learning, database persistence, 
and adaptive spaced repetition.
"""

import sys
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from flashcard_core import DatabaseManager, SpacedRepetitionEngine

# Style and Configuration Constants
FONT_FAMILY = "Segoe UI"
FONT_HELVETICA = "Helvetica"
APP_TITLE_STYLE = "AppTitle.TLabel"
HEADER_STYLE = "Header.TLabel"
STATS_VAL_STYLE = "StatsVal.TLabel"


# =====================================================================
# 1. GRAPHICAL USER INTERFACE (TKINTER)
# =====================================================================

class FlashcardApp(tk.Tk):
    """Integrated Tkinter Application Wrapper."""
    
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        
        self.title("Adeamus! Latein Vokabeltrainer")
        self.geometry("900x650")
        self.minimum_size = (800, 550)
        self.minsize(*self.minimum_size)
        
        # Configure overall style
        self.configure_styles()
        
        # State tracking
        self.active_engine = None
        self.current_card = None
        
        # Initialize primary screen container
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)
        
        # Load selection screen by default
        self.show_lesson_selection()

    def configure_styles(self):
        """Custom colors and typography."""
        self.style = ttk.Style(self)
        # Set theme (using standard 'clam' or 'aqua' depending on OS, fallback to clam)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass
            
        # Core Colors Configuration
        # Primary background: light silver / slate gray highlights
        self.style.configure(".", background="#f5f6fa")
        self.style.configure("TLabel", background="#f5f6fa", font=(FONT_FAMILY, 11))
        self.style.configure("TFrame", background="#f5f6fa")
        
        # Buttons Style
        self.style.configure("TButton", font=(FONT_FAMILY, 11), padding=6)
        self.style.configure("Primary.TButton", font=(FONT_FAMILY, 11, "bold"), background="#1e90ff", foreground="white")
        self.style.map("Primary.TButton", background=[("active", "#0077e6")])
        self.style.configure("Danger.TButton", font=(FONT_FAMILY, 11, "bold"), background="#d63031", foreground="white")
        
        # Title Fonts
        self.style.configure(APP_TITLE_STYLE, font=(FONT_HELVETICA, 22, "bold"), foreground="#2c3e50")
        self.style.configure(HEADER_STYLE, font=(FONT_HELVETICA, 14, "bold"), foreground="#34495e")
        self.style.configure(STATS_VAL_STYLE, font=("Courier", 14, "bold"), foreground="#2980b9")
        
        # Progressbar customization
        self.style.configure("Horizontal.TProgressbar", thickness=15, background="#2ecc71")

    def clear_container(self):
        """Destroys all active widgets in active container frame."""
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_lesson_selection(self):
        """Renders the Lesson Catalog view with embedded analytics and summaries."""
        self.clear_container()
        
        # High level container partitioning
        sidebar_width = 300
        
        # 1. SIDEBAR (Global metrics & difficult words list)
        sidebar = ttk.Frame(self.container, relief="solid", borderwidth=1, padding=15)
        sidebar.pack(side="left", fill="y", ipadx=5)
        
        sidebar_title = ttk.Label(sidebar, text="Statistiken", style="Header.TLabel")
        sidebar_title.pack(anchor="w", pady=(0, 15))
        
        # Load overall database statistics
        global_stats = self.db_manager.get_lesson_stats()
        
        stats_frame = ttk.LabelFrame(sidebar, text="Gesamtfortschritt", padding=10)
        stats_frame.pack(fill="x", pady=(0, 20))
        
        total_lbl = ttk.Label(stats_frame, text=f"Wörter gesamt: {global_stats['total']}")
        total_lbl.pack(anchor="w", pady=2)
        
        learned_lbl = ttk.Label(stats_frame, text=f"Gelernt (★≥3): {global_stats['learned']}")
        learned_lbl.pack(anchor="w", pady=2)
        
        avg_lbl = ttk.Label(stats_frame, text=f"Schnitt: {global_stats['avg_rating']} ⭐")
        avg_lbl.pack(anchor="w", pady=2)
        
        prog_bar = ttk.Progressbar(stats_frame, value=global_stats['progress_pct'], maximum=100)
        prog_bar.pack(fill="x", pady=(8, 2))
        
        prog_val = ttk.Label(stats_frame, text=f"{global_stats['progress_pct']}% abgeschlossen", font=(FONT_FAMILY, 9, "italic"))
        prog_val.pack(anchor="e")
        
        # Difficult Words Sub-panel
        diff_frame = ttk.LabelFrame(sidebar, text="Schwierige Wörter", padding=10)
        diff_frame.pack(fill="both", expand=True)
        
        diff_desc = ttk.Label(diff_frame, text="Niedrigste Bewertung & viele Abfragen:", font=(FONT_FAMILY, 9, "italic"), wraplength=sidebar_width-40)
        diff_desc.pack(anchor="w", pady=(0, 6))
        
        diff_words = self.db_manager.get_difficult_words(limit=5)
        if not diff_words:
            no_diff = ttk.Label(diff_frame, text="Keine schwierigen Wörter registriert.\nMach weiter so!", font=(FONT_FAMILY, 10), foreground="#27ae60", justify="center")
            no_diff.pack(expand=True, pady=10)
        else:
            for lekt, lat, ger, rating, count in diff_words:
                item_lbl = ttk.Label(
                    diff_frame, 
                    text=f"• L{lekt}: {lat}\n  → {ger} (Bew. {rating}/5, {count}x)",
                    font=(FONT_FAMILY, 9),
                    wraplength=sidebar_width-45,
                    justify="left"
                )
                item_lbl.pack(anchor="w", pady=4)
                
        # 2. MAIN HUB (Lesson collection list with natural scrolling)
        main_hub = ttk.Frame(self.container, padding=20)
        main_hub.pack(side="right", fill="both", expand=True)
        
        title_lbl = ttk.Label(main_hub, text="🎓 Adeamus! Latein Vokabeltrainer", style=APP_TITLE_STYLE)
        title_lbl.pack(anchor="w", pady=(0, 4))
        
        subtitle_lbl = ttk.Label(main_hub, text="Wähle eine Lektion, um das adaptive Abfragen zu starten.", font=(FONT_FAMILY, 11, "italic"), foreground="#7f8c8d")
        subtitle_lbl.pack(anchor="w", pady=(0, 20))
        
        # Grid frame container with a Canvas and standard scrollbar
        list_outer = ttk.Frame(main_hub)
        list_outer.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(list_outer, borderwidth=0, highlightthickness=0, background="#f5f6fa")
        scrollbar = ttk.Scrollbar(list_outer, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mousewheel scroll support
        def _on_mousewheel(event):
            # macOS uses scroll events, division checks platform compatibility
            if sys.platform == 'darwin':
                canvas.yview_scroll(int(-1 * event.delta), "units")
            else:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Fetch lessons and map lists
        all_lessons = self.db_manager.get_lessons()
        if not all_lessons:
            empty_lbl = ttk.Label(scrollable_frame, text="Keine Lektionen im System.\nDaten werden geladen oder synchronisiert...", font=(FONT_FAMILY, 12), justify="center")
            empty_lbl.pack(pady=40)
            return
            
        for idx, lektion in enumerate(all_lessons):
            stats = self.db_manager.get_lesson_stats(lektion)
            
            # Card element row container
            row_card = tk.Frame(
                scrollable_frame, 
                bg="white", 
                highlightbackground="#dfe6e9", 
                highlightthickness=1, 
                padx=15, 
                pady=12
            )
            row_card.pack(fill="x", expand=True, pady=6, padx=(0, 10))
            
            # Label section inside card
            lbl_container = tk.Frame(row_card, bg="white")
            lbl_container.pack(side="left", fill="both", expand=True)
            
            les_title = tk.Label(
                lbl_container, 
                text=f"Lektion {lektion}", 
                font=("Helvetica", 13, "bold"), 
                bg="white", 
                fg="#2c3e50"
            )
            les_title.pack(anchor="w", pady=(0, 2))
            
            summary_txt = f"{stats['total']} Wörter  |  {stats['learned']} gelernt  |  Schnitt: {stats['avg_rating']} ⭐"
            les_sub = tk.Label(
                lbl_container, 
                text=summary_txt, 
                font=(FONT_FAMILY, 9), 
                bg="white", 
                fg="#7f8c8d"
            )
            les_sub.pack(anchor="w")
            
            # Visual Progress Section
            bar_container = tk.Frame(row_card, bg="white")
            bar_container.pack(side="left", fill="x", padx=20, expand=True)
            
            lbl_pct = tk.Label(
                bar_container, 
                text=f"{stats['progress_pct']}%", 
                font=(FONT_FAMILY, 10, "bold"), 
                bg="white", 
                fg="#2ecc71"
            )
            lbl_pct.pack(anchor="e", pady=(0, 2))
            
            row_bar = ttk.Progressbar(bar_container, value=stats['progress_pct'], maximum=100, length=120)
            row_bar.pack(fill="x")
            
            # Action button
            start_btn = tk.Button(
                row_card, 
                text="Lernen", 
                font=(FONT_FAMILY, 10, "bold"),
                bg="#0984e3", 
                fg="white", 
                activebackground="#74b9ff",
                activeforeground="white",
                relief="flat",
                command=lambda lek=lektion: self.start_cards_session(lek)
            )
            start_btn.pack(side="right", padx=(10, 0), ipady=4, ipadx=10)

    def start_cards_session(self, lektion):
        """Initializes the adaptive repetition engine and prompts Study Screen."""
        self.active_engine = SpacedRepetitionEngine(self.db_manager, lektion)
        self.show_study_screen()

    def show_study_screen(self):
        """Study mode screen containing full interactive flip card UI."""
        self.clear_container()
        
        # Header navigation row
        header = ttk.Frame(self.container, padding=12)
        header.pack(fill="x")
        
        back_btn = ttk.Button(header, text="← Zurück zur Auswahl", command=self.exit_session)
        back_btn.pack(side="left")
        
        title_text = f"Lektion {self.active_engine.lektion} — Vokabeltrainer"
        session_title = ttk.Label(header, text=title_text, style=APP_TITLE_STYLE)
        session_title.pack(side="right", padx=10)
        
        # Interactive Study Content centering frame
        study_content = ttk.Frame(self.container, padding=(40, 20))
        study_content.pack(fill="both", expand=True)
        
        # Setup Flashcard container
        self.card_outer = tk.Frame(
            study_content, 
            bg="white", 
            relief="raised", 
            borderwidth=1, 
            highlightthickness=0
        )
        self.card_outer.pack(fill="both", expand=True, pady=(10, 20))
        
        # Subtitle/Status Inside Card
        self.card_meta = tk.Label(
            self.card_outer, 
            text="Abfrage-Status", 
            font=(FONT_FAMILY, 9, "italic"), 
            bg="white", 
            fg="#7f8c8d"
        )
        self.card_meta.pack(side="top", pady=10, fill="x")
        
        # Active Center Content (Latin term / German meaning)
        self.latin_lbl = tk.Label(
            self.card_outer, 
            text="Latin word", 
            font=("Helvetica", 24, "bold"), 
            bg="white", 
            fg="#2c3e50",
            wraplength=600
        )
        self.latin_lbl.pack(fill="both", expand=True)
        
        # Create separating line inside card container
        self.separator = tk.Frame(self.card_outer, height=2, bg="#f3f3f3")
        
        self.german_lbl = tk.Label(
            self.card_outer, 
            text="German meaning", 
            font=("Helvetica", 18), 
            bg="white", 
            fg="#0984e3",
            wraplength=600
        )
        
        # Action Bar container below Card
        self.action_panel = ttk.Frame(study_content)
        self.action_panel.pack(fill="x", pady=5)
        
        # Bind keyboard events for rapid rating workflow
        self.bind("<space>", lambda e: self.reveal_translation_action())
        self.bind("1", lambda e: self.submit_rating_action(1))
        self.bind("2", lambda e: self.submit_rating_action(2))
        self.bind("3", lambda e: self.submit_rating_action(3))
        self.bind("4", lambda e: self.submit_rating_action(4))
        self.bind("5", lambda e: self.submit_rating_action(5))
        
        # Load first card
        self.load_next_card_interactive()

    def load_next_card_interactive(self):
        """Requests selection from the repetition backend and presents front of card."""
        self.current_card = self.active_engine.get_next_card()
        
        if not self.current_card:
            messagebox.showinfo("Lektion abgeschlossen", "In dieser Lektion sind keine Wörter verfügbar.")
            self.show_lesson_selection()
            return
            
        # Hide translations and previous elements from card
        self.separator.pack_forget()
        self.german_lbl.pack_forget()
        
        # Bind dynamic meta labels
        last_rating = self.current_card['rating']
        prev_star = f"{last_rating} ⭐" if last_rating > 0 else "Unbewertet"
        meta_txt = f"Lektion {self.current_card['lektion']}  |  Letzte Bewertung: {prev_star}  |  Bisher abgefragt: {self.current_card['review_count']} mal"
        
        self.card_meta.config(text=meta_txt)
        self.latin_lbl.config(text=self.current_card['latin'])
        
        # Repartition action buttons layout
        for w in self.action_panel.winfo_children():
            w.destroy()
            
        reveal_btn = tk.Button(
            self.action_panel, 
            text="Antwort aufdecken (Leertaste)", 
            font=(FONT_FAMILY, 12, "bold"),
            bg="#0984e3", 
            fg="white", 
            relief="flat",
            activebackground="#74b9ff", 
            activeforeground="white",
            command=self.reveal_translation_action
        )
        reveal_btn.pack(ipady=8, ipadx=24, expand=True)

    def reveal_translation_action(self):
        """Displays German translation on card and offers scoring dock."""
        # Visual styling changes inside card
        self.separator.pack(fill="x", padx=100, pady=5)
        self.german_lbl.config(text=self.current_card['german'])
        self.german_lbl.pack(fill="both", expand=True)
        
        # Overwrite Action bar with 1-5 color rating buttons
        for w in self.action_panel.winfo_children():
            w.destroy()
            
        rate_header = ttk.Label(
            self.action_panel, 
            text="Wie gut hast du das Wort erinnert? (Tastatur: 1-5)", 
            font=(FONT_FAMILY, 10, "bold"),
            anchor="center"
        )
        rate_header.pack(fill="x", pady=(0, 8))
        
        buttons_dock = ttk.Frame(self.action_panel)
        buttons_dock.pack()
        
        # Colors dictionary for scoring labels (hex conversions)
        colors = {
            1: ("#ea8282", "#d63031"), # Red
            2: ("#ffbe76", "#e17055"), # Orange
            3: ("#f6e58d", "#f1c40f"), # Yellow
            4: ("#badc58", "#2ecc71"), # Light Green
            5: ("#6ab04c", "#27ae60"), # Green
        }
        
        labels = {
            1: "1: Gar nicht gewusst",
            2: "2: Fast gewusst",
            3: "3: Mit Mühe gewusst",
            4: "4: Gut gewusst",
            5: "5: Perfekt im Kopf",
        }
        
        for score in sorted(colors.keys()):
            bg, fg = colors[score]
            btn = tk.Button(
                buttons_dock, 
                text=labels[score], 
                font=(FONT_FAMILY, 9, "bold"),
                bg=bg, 
                fg="#1c1c1c",
                activebackground=fg,
                activeforeground="white",
                relief="flat",
                command=lambda s=score: self.submit_rating_action(s)
            )
            btn.pack(side="left", padx=5, ipady=6, ipadx=8)

    def submit_rating_action(self, score):
        """Saves score to DB, triggers UI updates, and moves to next card."""
        # Security shield if keyboard presses rating before revealing card
        if not self.german_lbl.winfo_viewable() and self.current_card is not None:
            # Let spacebar/enter act as automatic reveal
            self.reveal_translation_action()
            return
            
        if self.current_card:
            self.db_manager.update_rating(self.current_card['id'], score)
            self.load_next_card_interactive()

    def exit_session(self):
        """Cleans up keyboard events and returns back to the Catalog Overview."""
        self.unbind("<space>")
        self.unbind("1")
        self.unbind("2")
        self.unbind("3")
        self.unbind("4")
        self.unbind("5")
        self.active_engine = None
        self.current_card = None
        self.show_lesson_selection()


# =====================================================================
# 2. APP LAUNCH & BOOTSTRAP PIPELINE
# =====================================================================

def main():
    # Detect running workspace absolute pathing
    workspace_dir = Path("/Users/vw2ix71/Documents/Projekte/lateinAdemas")
    excel_path = workspace_dir / "out/adeamus_flashcards.xlsx"
    db_path = workspace_dir / "flashcards.db"
    
    # Configure DB Manager
    db_manager = DatabaseManager(db_path=str(db_path))
    
    # Populate DB on first run or additions detection
    print("Database manager initialized.")
    if os.path.exists(excel_path):
        print(f"Reading source vocabulary list: {excel_path}...")
        try:
            added = db_manager.sync_with_excel(excel_path=str(excel_path))
            print(f"Database sync completed containing new: {added} vocabulary entries!")
        except Exception as e:
            print(f"Warning: Excel spreadsheet parsing failed with error: {e}")
            print("Running database with existing dataset.")
    else:
        print(f"Could not locate {excel_path}. If database is empty, the trainer will have no active elements.")
        
    print("Starting Flashcard desktop interface...")
    app = FlashcardApp(db_manager)
    app.mainloop()


if __name__ == "__main__":
    main()
