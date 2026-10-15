import { t, translateNode } from "../lib/i18n";
import { useRef, useState } from "react";
import {
  BugIcon,
  CertificateIcon,
  GearSixIcon,
  MusicNoteIcon,
  PlaylistIcon,
  TranslateIcon,
  WaveformIcon,
  type Icon as PhosphorIcon,
} from "@phosphor-icons/react";
import logo from "../assets/humidi_logo.ico";
import type { PageId } from "../pages/pageIds";
import { Button } from "./Button";

const NAV_ITEMS: { id: PageId; label: string; icon: PhosphorIcon }[] = [
  { id: "playback", label: "演奏", icon: MusicNoteIcon },
  { id: "playlist", label: "歌单", icon: PlaylistIcon },
  { id: "visualizer", label: "可视化", icon: WaveformIcon },
  { id: "translator", label: "乐谱转换", icon: TranslateIcon },
  { id: "settings", label: "设置", icon: GearSixIcon },
  { id: "debug", label: "调试", icon: BugIcon },
  { id: "license", label: "关于", icon: CertificateIcon },
];

interface SidebarProps {
  activePage: PageId;
  onNavigate: (page: PageId) => void;
  visualizerDisabled?: boolean;
}

export function Sidebar({
  activePage,
  onNavigate,
  visualizerDisabled,
}: SidebarProps) {
  const [expanded, setExpanded] = useState(false);
  const collapseTimer = useRef<number | null>(null);

  function handleEnter() {
    if (collapseTimer.current) {
      window.clearTimeout(collapseTimer.current);
      collapseTimer.current = null;
    }
    setExpanded(true);
  }

  function handleLeave() {
    collapseTimer.current = window.setTimeout(() => setExpanded(false), 120);
  }

  return (
    <aside
      className={`sidebar${expanded ? " sidebar--expanded" : ""}`}
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
    >
      <div className="sidebar__logo">
        <img src={logo} alt="" width={24} height={24} />
        <span className="sidebar__wordmark">
          {t("Hu")}
          <i>{t("Midi")}</i>
          <small className="sidebar__edition">Xingkong</small>
        </span>
      </div>

      <nav className="sidebar__nav">
        {translateNode(
          NAV_ITEMS.map(({ id, label, icon: NavIcon }) => (
            <Button
              key={id}
              variant="nav"
              active={activePage === id}
              disabled={id === "visualizer" && visualizerDisabled}
              onClick={() => onNavigate(id)}
            >
              <NavIcon weight="duotone" />
              <span className="sidebar__nav-label">{translateNode(label)}</span>
            </Button>
          )),
        )}
      </nav>

      <div className="sidebar__spacer" />


    </aside>
  );
}
