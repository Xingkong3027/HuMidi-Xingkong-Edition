import { ask } from "./appDialogs";
import { parseMidiStructure } from "./tauri";
export async function parseMidiWithRepair(path: string, allowClip = false) {
  try {
    return {
      parsed: await parseMidiStructure(path),
      clip: false,
    };
  } catch (error) {
    if (
      !/data.?byte|out.of.range|invalid.*data|非法.*数据|数据.*越界/i.test(
        String(error),
      )
    )
      throw error;
    // A stored authorization belongs to this song. Even an authorized song
    // first tries unchanged bytes; structural errors never enter clipping.
    if (allowClip) {
      return { parsed: await parseMidiStructure(path, true), clip: true };
    }
    const repair = await ask(
      "这个 MIDI 含有超出规范范围的数据字节。是否尝试兼容修复？只修复导入数据，原始文件保持不变。",
      {
        title: "非标准 MIDI",
        kind: "warning",
        okLabel: "尝试修复",
        cancelLabel: "取消导入",
      },
    );
    if (!repair) throw new Error("已取消 MIDI 导入");
    return { parsed: await parseMidiStructure(path, true), clip: true };
  }
}
