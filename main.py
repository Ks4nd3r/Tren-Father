"""Offline workout diary for desktop and Android."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from catalog import EXERCISES
from storage import WorkoutStore, parse_workout_date


def label(text: str, height: int = 36) -> Label:
    return Label(text=text, size_hint_y=None, height=dp(height), halign="left", valign="middle")


def button(text: str, callback, height: int = 48) -> Button:
    result = Button(text=text, size_hint_y=None, height=dp(height))
    result.bind(on_release=callback)
    return result


class WorkoutApp(App):
    title = "Дневник тренировок"

    def build(self):
        self.store = WorkoutStore(Path(self.user_data_dir) / "workouts.db")
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        tabs = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        tabs.add_widget(button("Запись", lambda *_: self.show_entry()))
        tabs.add_widget(button("История", lambda *_: self.show_history()))
        root.add_widget(tabs)
        self.content = BoxLayout(orientation="vertical")
        root.add_widget(self.content)
        self.build_entry()
        return root

    def on_stop(self):
        self.store.close()

    def show_message(self, title: str, message: str):
        body = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        body.add_widget(Label(text=message, halign="center"))
        close = button("Понятно", lambda *_: popup.dismiss())
        body.add_widget(close)
        popup = Popup(title=title, content=body, size_hint=(0.9, 0.45))
        popup.open()

    def replace_content(self, widget):
        self.content.clear_widgets()
        self.content.add_widget(widget)

    def build_entry(self):
        scroll = ScrollView()
        form = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))
        form.add_widget(label("Дата (ГГГГ-ММ-ДД)"))
        self.date_input = TextInput(text=date.today().isoformat(), multiline=False,
                                    size_hint_y=None, height=dp(48))
        form.add_widget(self.date_input)
        form.add_widget(label("Группа мышц"))
        self.group_spinner = Spinner(text="Выберите группу", values=tuple(EXERCISES),
                                     size_hint_y=None, height=dp(48))
        self.group_spinner.bind(text=self.on_group_changed)
        form.add_widget(self.group_spinner)
        form.add_widget(label("Упражнение"))
        self.exercise_spinner = Spinner(text="Выберите упражнение", values=(),
                                        size_hint_y=None, height=dp(48))
        form.add_widget(self.exercise_spinner)
        form.add_widget(button("Открыть упражнение", self.open_exercise))
        self.current_label = label("Подходы: выберите дату и упражнение", 48)
        form.add_widget(self.current_label)
        form.add_widget(label("Повторы                             Вес, кг"))
        self.sets_container = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        self.sets_container.bind(minimum_height=self.sets_container.setter("height"))
        form.add_widget(self.sets_container)
        form.add_widget(button("+ Добавить подход", self.add_set))
        form.add_widget(button("Сохранить упражнение", self.save_exercise))
        scroll.add_widget(form)
        self.entry_scroll = scroll
        self.replace_content(scroll)
        self.opened_key = None

    def show_entry(self):
        if not hasattr(self, "date_input"):
            self.build_entry()
        else:
            self.replace_content(self.entry_scroll)

    def on_group_changed(self, _spinner, group):
        self.exercise_spinner.values = EXERCISES.get(group, ())
        self.exercise_spinner.text = "Выберите упражнение"
        self.opened_key = None
        self.sets_container.clear_widgets()
        self.current_label.text = "Подходы: выберите упражнение"

    def open_exercise(self, *_):
        try:
            workout_date = parse_workout_date(self.date_input.text.strip()).isoformat()
            group = self.group_spinner.text
            exercise = self.exercise_spinner.text
            if group not in EXERCISES or exercise not in EXERCISES[group]:
                raise ValueError("Выберите группу мышц и упражнение")
            key = (workout_date, group, exercise)
            if self.opened_key != key:
                self.sets_container.clear_widgets()
                for reps, weight in self.store.get_sets(*key):
                    self.add_set(reps=reps, weight=weight)
                if not self.sets_container.children:
                    self.add_set()
            self.opened_key = key
            self.current_label.text = f"{exercise} — {workout_date}"
        except ValueError as error:
            self.show_message("Проверьте ввод", str(error))

    def add_set(self, *_args, reps: int | str = "", weight: float | str = ""):
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        reps_input = TextInput(text=str(reps), hint_text="Повторы", input_filter="int",
                               multiline=False)
        weight_input = TextInput(text=f"{weight:g}" if isinstance(weight, (int, float)) else weight,
                                 hint_text="Вес, кг", input_filter="float", multiline=False)
        row.add_widget(reps_input)
        row.add_widget(weight_input)
        row.add_widget(button("×", lambda *_: self.sets_container.remove_widget(row)))
        self.sets_container.add_widget(row)

    def save_exercise(self, *_):
        try:
            key = (self.date_input.text.strip(), self.group_spinner.text, self.exercise_spinner.text)
            if key != self.opened_key:
                raise ValueError("Сначала откройте упражнение для выбранной даты")
            sets = []
            for row in reversed(self.sets_container.children):
                reps_text = row.children[2].text.strip()
                weight_text = row.children[1].text.strip().replace(",", ".")
                if not reps_text or not weight_text:
                    raise ValueError("Заполните повторы и вес в каждом подходе")
                sets.append((int(reps_text), float(weight_text)))
            self.store.save_exercise(*key, sets)
            self.show_message("Сохранено", f"{key[2]}: {len(sets)} подход(а/ов)")
        except ValueError as error:
            self.show_message("Проверьте ввод", str(error))

    def show_history(self, *_):
        scroll = ScrollView()
        body = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        body.bind(minimum_height=body.setter("height"))
        body.add_widget(label("Сохранённые тренировки", 48))
        workouts = self.store.list_workouts()
        if not workouts:
            body.add_widget(label("Записей пока нет", 48))
        for workout_date, exercises, sets in workouts:
            body.add_widget(button(
                f"{workout_date}    {exercises} упр. / {sets} подх.",
                lambda _btn, day=workout_date: self.show_workout(day),
            ))
        body.add_widget(label("Очистка старых записей", 48))
        body.add_widget(label("Удалить тренировки старше (дней):"))
        self.retention_input = TextInput(text="365", input_filter="int", multiline=False,
                                         size_hint_y=None, height=dp(48))
        body.add_widget(self.retention_input)
        body.add_widget(button("Очистить старые данные", self.confirm_cleanup))
        scroll.add_widget(body)
        self.replace_content(scroll)

    def show_workout(self, workout_date: str):
        details = self.store.workout_details(workout_date)
        body = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
        scroll = ScrollView()
        rows = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        rows.bind(minimum_height=rows.setter("height"))
        previous_exercise = None
        for group, exercise, position, reps, weight in details:
            if previous_exercise != (group, exercise):
                rows.add_widget(label(f"{group} · {exercise}", 42))
                previous_exercise = (group, exercise)
            rows.add_widget(label(f"  Подход {position}: {reps} × {weight:g} кг", 34))
        scroll.add_widget(rows)
        body.add_widget(scroll)
        body.add_widget(button("Закрыть", lambda *_: popup.dismiss()))
        popup = Popup(title=workout_date, content=body, size_hint=(0.95, 0.8))
        popup.open()

    def confirm_cleanup(self, *_):
        try:
            days = int(self.retention_input.text)
            count = self.store.count_older_than(days)
        except ValueError as error:
            self.show_message("Проверьте период", str(error))
            return
        if count == 0:
            self.show_message("Очистка", "Записей старше указанного периода нет")
            return
        body = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        body.add_widget(Label(text=f"Удалить {count} тренировок старше {days} дней?"))
        body.add_widget(button("Удалить", lambda *_: self.perform_cleanup(days, popup)))
        body.add_widget(button("Отмена", lambda *_: popup.dismiss()))
        popup = Popup(title="Подтвердите удаление", content=body, size_hint=(0.9, 0.5))
        popup.open()

    def perform_cleanup(self, days: int, popup: Popup):
        removed = self.store.delete_older_than(days)
        popup.dismiss()
        self.show_history()
        self.show_message("Очистка", f"Удалено тренировок: {removed}")


if __name__ == "__main__":
    WorkoutApp().run()
