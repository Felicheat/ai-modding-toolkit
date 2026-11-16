"""Tiny T3D writer for Blueprint graph nodes (paste with Ctrl+V into a graph).

Format taken from nodes copied out of this kit's editor. Pins are written in full; links as LinkedTo=(NodeName PinId,).
"""
import uuid

G = lambda: uuid.uuid4().hex.upper()
T = ("PinType.PinSubCategoryMemberReference=(),PinType.PinValueType=(),PinType.ContainerType=None,"
     "PinType.bIsReference=False,PinType.bIsConst=False,PinType.bIsWeakPointer=False,"
     "PinType.bIsUObjectWrapper=False,PinType.bSerializeAsSinglePrecisionFloat=False,")
F = ("PersistentGuid=00000000000000000000000000000000,bHidden=%s,bNotConnectable=False,"
     "bDefaultValueIsReadOnly=False,bDefaultValueIsIgnored=False,bAdvancedView=%s,bOrphanedPin=False,)")
TGT = 'PinFriendlyName=NSLOCTEXT("K2Node", "Target", "Target"),'


def cls(path):
    """'/Script/Stalker2.PC' -> quoted class reference used in pin types."""
    return "\"/Script/CoreUObject.Class'%s'\"" % path


def pin(pid, name, cat, sub="None", subcat="", out=False, links=(), hidden=False, adv=False, extra=""):
    l = ("LinkedTo=(" + "".join(f"{n} {p}," for n, p in links) + "),") if links else ""
    d = 'Direction="EGPD_Output",' if out else ""
    return (f'   CustomProperties Pin (PinId={pid},PinName="{name}",{extra}{d}PinType.PinCategory="{cat}",'
            f'PinType.PinSubCategory="{subcat}",PinType.PinSubCategoryObject={sub},{T}{l}'
            + F % ("True" if hidden else "False", "True" if adv else "False"))


def head(klass, name, x, y, comment="", body=()):
    s = [f'Begin Object Class={klass} Name="{name}"'] + ["   " + b for b in body]
    s += [f"   NodePosX={x}", f"   NodePosY={y}"]
    if comment:
        s += ["   bCommentBubbleVisible=True", f'   NodeComment="{comment}"']
    s += [f"   NodeGuid={G()}"]
    return s


def comment_box(name, x, y, w, h, text):
    return [f'Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="{name}"',
            f"   NodePosX={x}", f"   NodePosY={y}", f"   NodeWidth={w}", f"   NodeHeight={h}",
            f'   NodeComment="{text}"', f"   NodeGuid={G()}", "End Object"]


def write(path, lines):
    open(path, "w", newline="\r\n", encoding="utf-8").write("\n".join(lines) + "\n")


# Copied from the Stalker 2 modding harness, https://github.com/noahsemus/stalker2-modding-harness (commit 4b2069a8).
# MIT License, Copyright (c) 2026 Noah Semus. Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above
# copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
