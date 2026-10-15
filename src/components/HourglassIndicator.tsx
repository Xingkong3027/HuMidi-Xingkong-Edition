import { translateNode } from "../lib/i18n";
import { useEffect, useState } from "react";

const HOURGLASS_FRAMES = ["◳", "◴", "◵", "◶"];

export function HourglassIndicator() {
  const [frame, setFrame] = useState(0);

  useEffect(() => {
    const id = setInterval(
      () => setFrame((f) => (f + 1) % HOURGLASS_FRAMES.length),
      350,
    );
    return () => clearInterval(id);
  }, []);

  return (
    <span className="hourglass-indicator">
      {translateNode(HOURGLASS_FRAMES[frame])}
    </span>
  );
}
