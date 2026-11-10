with open('core/engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """    def run(self) -> None:
        self.is_running = True

        while self.is_running:"""

replacement = """    def _translate_joystick_event(self, event: pygame.event.Event) -> list:
        \"\"\"Traduce eventos de gamepad a teclado virtual para compatibilidad universal.\"\"\"
        translated = []
        if event.type == pygame.JOYBUTTONDOWN:
            if event.button == 0:
                translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE, "unicode": " "}))
            elif event.button in (1, 6, 7):
                translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE, "unicode": ""}))
            elif event.button in (2, 3):
                translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN, "unicode": "\\r"}))
        elif event.type == pygame.JOYHATMOTION:
            hx, hy = event.value
            if hx < 0:
                translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_LEFT, "unicode": ""}))
            elif hx > 0:
                translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RIGHT, "unicode": ""}))
            if hy > 0:
                translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_UP, "unicode": ""}))
            elif hy < 0:
                translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_DOWN, "unicode": ""}))
        elif event.type == pygame.JOYAXISMOTION:
            deadzone = 0.45
            if event.axis == 0:
                if event.value < -deadzone:
                    translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_LEFT, "unicode": ""}))
                elif event.value > deadzone:
                    translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RIGHT, "unicode": ""}))
            elif event.axis == 1:
                if event.value < -deadzone:
                    translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_UP, "unicode": ""}))
                elif event.value > deadzone:
                    translated.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_DOWN, "unicode": ""}))
        return translated

    def run(self) -> None:
        self.is_running = True

        while self.is_running:"""

assert target in content, "target not found in content"
content = content.replace(target, replacement, 1)

loop_target = """                if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                    event = self._map_mouse_event(event)

                self.state_machine.handle_event(event)"""

loop_replacement = """                if event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                    self._refresh_joysticks()
                    continue

                if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                    event = self._map_mouse_event(event)

                self.state_machine.handle_event(event)

                if event.type in (pygame.JOYBUTTONDOWN, pygame.JOYHATMOTION, pygame.JOYAXISMOTION):
                    for virt_evt in self._translate_joystick_event(event):
                        self.state_machine.handle_event(virt_evt)"""

assert loop_target in content, "loop_target not found in content"
content = content.replace(loop_target, loop_replacement, 1)

with open('core/engine.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS ENGINE PATCH")
