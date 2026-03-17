import os
import sys
import bisect
import numpy as np
from typing import List, Optional, Callable

from core.models import Note, MusicalSection, KeyEvent
from core.core import get_time_groups

# Cached weights — loaded once on first AI pedal call.
_weights = None


def _get_model_path() -> str:
    base = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'pedal_bilstm.npz')


def _load_weights() -> Optional[dict]:
    path = _get_model_path()
    if not os.path.exists(path):
        return None
    npz = np.load(path)
    return {
        'lstm1_W': npz['lstm1_W'],    # (2, 1024, 140)
        'lstm1_R': npz['lstm1_R'],    # (2, 1024, 256)
        'lstm1_B': npz['lstm1_B'],    # (2, 2048)
        'lstm2_W': npz['lstm2_W'],    # (2, 1024, 512)
        'lstm2_R': npz['lstm2_R'],    # (2, 1024, 256)
        'lstm2_B': npz['lstm2_B'],    # (2, 2048)
        'linear_W': npz['linear_W'],  # (512, 1)
        'linear_B': npz['linear_B'],  # (1,)
    }


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _lstm_direction(x_seq: np.ndarray, W: np.ndarray, R: np.ndarray,
                    B: np.ndarray, H: int) -> np.ndarray:
    """Single-direction LSTM over a sequence. ONNX gate order: i, o, f, c."""
    bias = B[:4*H] + B[4*H:]  # combine Wb and Rb
    h = np.zeros(H, dtype=np.float32)
    c = np.zeros(H, dtype=np.float32)
    out = np.empty((len(x_seq), H), dtype=np.float32)
    for t, x in enumerate(x_seq):
        gates = x @ W.T + h @ R.T + bias
        i = _sigmoid(gates[0*H:1*H])
        o = _sigmoid(gates[1*H:2*H])
        f = _sigmoid(gates[2*H:3*H])
        g = np.tanh(gates[3*H:4*H])
        c = f * c + i * g
        h = o * np.tanh(c)
        out[t] = h
    return out


def _bilstm_layer(x_seq: np.ndarray, W: np.ndarray, R: np.ndarray,
                  B: np.ndarray, H: int) -> np.ndarray:
    """Bidirectional LSTM layer. Returns (T, 2*H)."""
    fwd = _lstm_direction(x_seq,        W[0], R[0], B[0], H)
    bwd = _lstm_direction(x_seq[::-1],  W[1], R[1], B[1], H)[::-1]
    return np.concatenate([fwd, bwd], axis=1)


def _bilstm_forward(x: np.ndarray, weights: dict) -> np.ndarray:
    """Full 2-layer BiLSTM + linear head. x: (1, T, 140) → preds: (T,)."""
    seq = x[0]  # (T, 140)
    out1 = _bilstm_layer(seq,  weights['lstm1_W'], weights['lstm1_R'], weights['lstm1_B'], 256)
    out2 = _bilstm_layer(out1, weights['lstm2_W'], weights['lstm2_R'], weights['lstm2_B'], 256)
    logits = out2 @ weights['linear_W'] + weights['linear_B']  # (T, 1)
    return _sigmoid(logits[:, 0])  # (T,)


def generate_events(config: dict, final_notes: List[Note], sections: List[MusicalSection],
                    debug_log: Optional[Callable[[str], None]] = None) -> List[KeyEvent]:
    style = config.get('pedal_style')
    if style == 'none':
        if debug_log is not None:
            debug_log("[PEDAL] Style: none — no pedal events generated")
        return []
    events = []

    if style == 'ai':
        ai_events = _generate_ai_pedal(final_notes, debug_log)
        if ai_events:
            return ai_events
        if debug_log is not None:
            debug_log("[PEDAL] AI output rejected or unavailable — falling back to adaptive algorithm")
        bass_notes = [n for n in final_notes if n.hand == 'left']
        bass_notes.sort(key=lambda n: n.start_time)
        if not bass_notes:
            treble_notes = [n for n in final_notes if n.hand == 'right']
            treble_notes.sort(key=lambda n: n.start_time)
            return _generate_adaptive_pedal_driver(treble_notes, final_notes, debug_log)
        return _generate_adaptive_pedal_driver(bass_notes, final_notes, debug_log)

    if style == 'hybrid':
        # TODO: re-enable when Pedal AI is integrated
        if config.get('use_ai_pedal', True):
            ai_events = _generate_ai_pedal(final_notes, debug_log)
            if ai_events:
                return ai_events
            if debug_log is not None:
                debug_log("[PEDAL] AI output rejected or unavailable — falling back to adaptive algorithm")
        else:
            if debug_log is not None:
                debug_log("[PEDAL] AI disabled by user — using adaptive algorithm")

        bass_notes = [n for n in final_notes if n.hand == 'left']
        bass_notes.sort(key=lambda n: n.start_time)
        if not bass_notes:
            treble_notes = [n for n in final_notes if n.hand == 'right']
            treble_notes.sort(key=lambda n: n.start_time)
            if debug_log is not None:
                debug_log(f"[PEDAL] Adaptive driver: using {len(treble_notes)} RIGHT-hand notes (no bass notes)")
            result = _generate_adaptive_pedal_driver(treble_notes, final_notes, debug_log)
            return result
        if debug_log is not None:
            debug_log(f"[PEDAL] Adaptive driver: using {len(bass_notes)} LEFT-hand bass notes")
        return _generate_adaptive_pedal_driver(bass_notes, final_notes, debug_log)

    if debug_log is not None:
        debug_log(f"[PEDAL] Style: {style} | Sections: {len(sections)}")

    sections_no_lh = 0
    for section in sections:
        lh_notes = [n for n in section.notes if n.hand == 'left']
        lh_notes.sort(key=lambda n: n.start_time)
        if not lh_notes:
            start = section.notes[0].start_time
            end = max(n.end_time for n in section.notes)
            events.append(KeyEvent(start, 1, 'pedal', 'down'))
            events.append(KeyEvent(end, 0, 'pedal', 'up'))
            sections_no_lh += 1
            continue

        if style == 'rhythmic':
            groups = get_time_groups(lh_notes)
            for g in groups:
                start = g[0].start_time
                end = max(n.end_time for n in g)
                events.append(KeyEvent(start, 1, 'pedal', 'down'))
                events.append(KeyEvent(end, 0, 'pedal', 'up'))
        else:
            _generate_harmonic_pedal(events, lh_notes)

    if debug_log is not None:
        downs = sum(1 for e in events if e.key_char == 'down')
        debug_log(
            f"[PEDAL] {style} result: {len(events)} events ({downs} downs, {len(events) - downs} ups) | "
            f"sections_without_LH={sections_no_lh}"
        )
    return events


def _generate_ai_pedal(notes: List[Note], debug_log: Optional[Callable[[str], None]]) -> List[KeyEvent]:
    global _weights
    fps = 50.0

    if not os.path.exists(_get_model_path()):
        if debug_log is not None:
            debug_log("AI generation skipped: Model not found.")
        return []

    if _weights is None:
        try:
            _weights = _load_weights()
        except Exception as e:
            if debug_log is not None:
                debug_log(f"AI generation aborted: Failed to load weights -> {e}")
            return []

    # 2. Matrix Translation
    max_time = max(note.end_time for note in notes)
    total_steps = int(np.ceil(max_time * fps)) + 1
    input_tensor = np.zeros((1, total_steps, 128), dtype=np.float32)

    for note in notes:
        s_idx = int(note.start_time * fps)
        e_idx = int(note.end_time * fps)
        input_tensor[0, s_idx:e_idx, note.pitch] = note.velocity / 127.0

    # 3. Chroma Augmentation
    chroma = np.stack([input_tensor[0, :, c::12].sum(axis=1) for c in range(12)], axis=1)  # (T, 12)
    input_tensor = np.concatenate([input_tensor[0], chroma], axis=1)[np.newaxis]  # (1, T, 140)

    # 4. NumPy BiLSTM Forward Pass
    try:
        preds = _bilstm_forward(input_tensor, _weights)  # (T,)
    except Exception as e:
        if debug_log is not None:
            debug_log(f"AI execution crashed during forward pass: {e}")
        return []

    # 5. Silence Masking
    is_silent = np.ones(total_steps, dtype=bool)
    for note in notes:
        s_idx = int(note.start_time * fps)
        e_idx = int((note.end_time + 0.35) * fps)
        is_silent[s_idx:min(e_idx, total_steps)] = False

    preds[is_silent] = 0.0

    # 6. Physical Mechanism Event Generation
    events = []
    pedal_is_down = False
    single_threshold = 0.70
    last_up_time = -1.0
    PEDAL_LAG = 0.05

    for i in range(1, len(preds)):
        prev_val = preds[i-1]
        curr_val = preds[i]
        curr_time = i / fps

        if prev_val < single_threshold and curr_val >= single_threshold:
            if not pedal_is_down:
                actual_down_time = curr_time
                if actual_down_time - last_up_time < PEDAL_LAG:
                    actual_down_time = last_up_time + PEDAL_LAG
                pedal_is_down = True
                events.append(KeyEvent(actual_down_time, 1, 'pedal', 'down'))

        elif prev_val >= single_threshold and curr_val < single_threshold:
            if pedal_is_down:
                pedal_is_down = False
                events.append(KeyEvent(curr_time, 0, 'pedal', 'up'))
                last_up_time = curr_time

    if pedal_is_down:
        events.append(KeyEvent(max_time, 0, 'pedal', 'up'))

    # 7. Quality Assurance Rejection
    if len(events) <= 2:
        if debug_log is not None:
            debug_log("AI pipeline output rejected (Insufficient mathematical variance).")
        return []

    if debug_log is not None:
        debug_log(f"AI pipeline successful: Queued {len(events)} physical actuations.")

    return events


def _generate_adaptive_pedal_driver(driver_notes: List[Note], all_notes: List[Note],
                                    debug_log: Optional[Callable[[str], None]] = None) -> List[KeyEvent]:
    events = []
    if not driver_notes:
        if debug_log is not None:
            debug_log("[PEDAL] Adaptive: no driver notes — returning empty")
        return events

    PEDAL_LAG = 0.05
    UNSAFE_INTERVALS = {1, 6}
    all_note_times = [n.start_time for n in all_notes]
    gap_lifts = 0
    interval_repedals = 0
    vertical_repedals = 0

    for i in range(len(driver_notes)):
        curr = driver_notes[i]
        next_n = driver_notes[i+1] if i < len(driver_notes) - 1 else None

        if i == 0:
            events.append(KeyEvent(curr.start_time, 1, 'pedal', 'down'))

        gap = next_n.start_time - curr.end_time if next_n else 0.0

        if gap > 0.35:
            events.append(KeyEvent(curr.end_time, 0, 'pedal', 'up'))
            if next_n:
                events.append(KeyEvent(next_n.start_time, 1, 'pedal', 'down'))
            gap_lifts += 1
        else:
            should_repedal = False
            repedal_reason = None

            if next_n:
                linear_interval = abs(next_n.pitch - curr.pitch) % 12
                if linear_interval in UNSAFE_INTERVALS:
                    should_repedal = True
                    repedal_reason = 'linear_interval'

                if not should_repedal:
                    lo = bisect.bisect_left(all_note_times, next_n.start_time - 0.05)
                    hi = bisect.bisect_right(all_note_times, next_n.start_time + 0.05)
                    concurrent_notes = all_notes[lo:hi]
                    if concurrent_notes:
                        lowest_pitch = min(n.pitch for n in concurrent_notes)
                        for n in concurrent_notes:
                            vertical_interval = abs(n.pitch - lowest_pitch) % 12
                            if vertical_interval in UNSAFE_INTERVALS:
                                should_repedal = True
                                repedal_reason = 'vertical_interval'
                                break

            if should_repedal and next_n:
                events.append(KeyEvent(next_n.start_time, 0, 'pedal', 'up'))
                events.append(KeyEvent(next_n.start_time + PEDAL_LAG, 1, 'pedal', 'down'))
                if repedal_reason == 'linear_interval':
                    interval_repedals += 1
                else:
                    vertical_repedals += 1

    final_end = max(n.end_time for n in driver_notes)
    events.append(KeyEvent(final_end, 0, 'pedal', 'up'))

    if debug_log is not None:
        downs = sum(1 for e in events if e.key_char == 'down')
        debug_log(
            f"[PEDAL] Adaptive result: {len(events)} events ({downs} downs) | "
            f"gap_lifts={gap_lifts} interval_repedals={interval_repedals} vertical_repedals={vertical_repedals}"
        )
    return events


def _generate_harmonic_pedal(events: List[KeyEvent], bass_notes: List[Note]):
    if not bass_notes: return
    current_bass_pitch = -1
    for i, note in enumerate(bass_notes):
        is_new_harmony = (note.pitch != current_bass_pitch)
        if i == 0:
            events.append(KeyEvent(note.start_time, 1, 'pedal', 'down'))
        else:
            prev_end = bass_notes[i-1].end_time
            has_gap = (note.start_time - prev_end) > 0.15
        if i > 0 and has_gap:
            events.append(KeyEvent(prev_end, 0, 'pedal', 'up'))
            events.append(KeyEvent(note.start_time, 1, 'pedal', 'down'))
        elif is_new_harmony:
            events.append(KeyEvent(note.start_time, 0, 'pedal', 'up'))
            events.append(KeyEvent(note.start_time, 1, 'pedal', 'down'))
        current_bass_pitch = note.pitch
    final_end = max(n.end_time for n in bass_notes)
    events.append(KeyEvent(final_end, 0, 'pedal', 'up'))
