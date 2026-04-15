import Live
from _Framework.ControlSurface import ControlSurface
from _Framework.TransportComponent import TransportComponent
from _Framework.DeviceComponent import DeviceComponent
from _Framework.MixerComponent import MixerComponent
from _Framework.ButtonElement import ButtonElement
from _Framework.EncoderElement import EncoderElement
from _Framework.SliderElement import SliderElement
from _Framework.InputControlElement import MIDI_CC_TYPE, MIDI_NOTE_TYPE

# ---------------------------------------------------------------------------
# M-Audio Code 25 — MIDI mapping constants
# Channel values are ZERO-INDEXED (0 = Ch1, 9 = Ch10).
# ---------------------------------------------------------------------------

CHANNEL = 1  # Channel 2 (zero-indexed)

# 4 Knobs — mapped to device macros 5-8
KNOB_CCS = [35, 41, 44, 45]

# 5 Faders — first 4 mapped to device macros 1-4, last one is master volume
FADER_CCS = [63, 75, 76, 77]
MASTER_FADER_CC = 62

# Pads for clip launch on channel 10 (12-semitone shift, 3 rows per octave)
# Octave 1 (notes 48-59):  tracks 1-4,   scenes 1-3
# Octave 2 (notes 60-71):  tracks 5-8,   scenes 1-3
# Octave 3 (notes 72-83):  tracks 9-12,  scenes 1-3
# Octave 4 (notes 84-95):  tracks 13-16, scenes 1-3
# Octave 5 (notes 96-107): tracks 17-20, scenes 1-3
PAD_CHANNEL = 9

# Mod wheel (MW1) — tempo
TEMPO_CC = 1

# Transport buttons
PLAY_CC = 119
STOP_CC = 118
RECORD_CC = 120
LOOP_CC = 114
REWIND_CC = 116
FORWARD_CC = 117


class MaudioCode25(ControlSurface):

    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        with self.component_guard():
            self._setup_transport()
            self._setup_device()
            self._setup_master()
            self._setup_session()
        self.log_message("MaudioCode25 remote script loaded")

    def disconnect(self):
        self.log_message("MaudioCode25 remote script unloaded")
        ControlSurface.disconnect(self)

    # -- Transport + tempo --------------------------------------------------

    def _setup_transport(self):
        transport = TransportComponent()
        transport.set_play_button(self._make_button(PLAY_CC, "Play"))
        self._stop_button = self._make_button(STOP_CC, "Stop")
        self._stop_button.add_value_listener(self._on_stop)
        transport.set_record_button(self._make_button(RECORD_CC, "Record"))
        transport.set_loop_button(self._make_button(LOOP_CC, "Loop"))
        transport.set_seek_forward_button(self._make_button(FORWARD_CC, "Forward"))
        transport.set_seek_backward_button(self._make_button(REWIND_CC, "Rewind"))
        transport.set_tempo_control(self._make_encoder(TEMPO_CC, "Tempo"))

    def _on_stop(self, value):
        if value > 0:
            self.song().stop_playing()
            self.song().stop_all_clips()

    # -- Device macros (faders 1-4 = macros 1-4, knobs 1-4 = macros 5-8) ---

    def _setup_device(self):
        device = DeviceComponent()
        device.set_on_off_button(None)

        macros = []
        for i, cc in enumerate(FADER_CCS):
            macros.append(self._make_slider(cc, "Fader_" + str(i + 1)))
        for i, cc in enumerate(KNOB_CCS):
            macros.append(self._make_encoder(cc, "Knob_" + str(i + 1)))

        device.set_parameter_controls(tuple(macros))
        self.set_device_component(device)

    # -- Master fader -------------------------------------------------------

    def _setup_master(self):
        mixer = MixerComponent(0)
        mixer.master_strip().set_volume_control(
            self._make_slider(MASTER_FADER_CC, "Master_Fader")
        )

    # -- Session (oct 1 = tracks 1-4, oct 2 = 5-8, oct 3 = 9-12) -----------
    # Toggle: press to launch, press again to stop.

    def _setup_session(self):
        self._pads = []
        for note in range(48, 108):
            block = (note - 48) // 12
            within = (note - 48) % 12
            row = 2 - (within // 4)
            col = within % 4 + (block * 4)
            pad = self._make_pad(note, "Pad_" + str(note))
            pad.add_value_listener(lambda value, r=row, c=col: self._on_pad(value, r, c))
            self._pads.append(pad)

    def _on_pad(self, value, row, col):
        if value == 0:
            return
        tracks = self.song().tracks
        if col < len(tracks):
            clip_slots = tracks[col].clip_slots
            if row < len(clip_slots):
                cs = clip_slots[row]
                if cs.has_clip and cs.clip.is_playing:
                    cs.stop()
                else:
                    cs.fire()

    # -- Helpers ------------------------------------------------------------

    def _make_button(self, cc, name):
        return ButtonElement(True, MIDI_CC_TYPE, CHANNEL, cc, name=name)

    def _make_encoder(self, cc, name):
        return EncoderElement(
            MIDI_CC_TYPE, CHANNEL, cc, Live.MidiMap.MapMode.absolute, name=name
        )

    def _make_slider(self, cc, name):
        return SliderElement(MIDI_CC_TYPE, CHANNEL, cc, name=name)

    def _make_pad(self, note, name):
        return ButtonElement(True, MIDI_NOTE_TYPE, PAD_CHANNEL, note, name=name)
