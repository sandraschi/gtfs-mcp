import { BookOpen } from "lucide-react";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE } from "@/lib/api";

interface Skill {
  name: string;
  description: string;
}

export function Skills() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/skills`)
      .then((r) => r.json())
      .then((d) => {
        setSkills((d.skills ?? []) as Skill[]);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const openSkill = async (name: string) => {
    setSelected(name);
    setContent("");
    try {
      const r = await fetch(`${API_BASE}/skill/${name}`);
      setContent(await r.text());
    } catch {
      setContent("Failed to load skill content.");
    }
  };

  return (
    <div data-testid="skills-page" className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Skills</h2>
        <p className="text-sm text-slate-300">
          Skill documents that teach the chat assistant how to use this server.
        </p>
      </div>

      {loading && <p className="text-sm text-slate-400">Loading skills...</p>}

      <div className="grid gap-4 lg:grid-cols-[300px_1fr]">
        <div className="space-y-2">
          {skills.map((s) => (
            <button
              type="button"
              key={s.name}
              data-testid={`skill-${s.name}`}
              onClick={() => openSkill(s.name)}
              className={`flex w-full items-start gap-2 rounded-lg border px-3 py-2.5 text-left transition-colors ${
                selected === s.name
                  ? "border-blue-600 bg-blue-600/10"
                  : "border-slate-800 bg-slate-900/40 hover:bg-slate-800"
              }`}
            >
              <BookOpen className="mt-0.5 h-4 w-4 shrink-0 text-blue-400" />
              <span>
                <span className="block text-sm font-medium text-slate-200">
                  {s.name}
                </span>
                <span className="block text-xs text-slate-400">
                  {s.description}
                </span>
              </span>
            </button>
          ))}
        </div>

        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader>
            <CardTitle className="text-white">
              {selected ?? "Skill Content"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!selected && (
              <p className="text-sm text-slate-400">
                Select a skill to read its content.
              </p>
            )}
            {selected && !content && (
              <p className="text-sm text-slate-400">Loading...</p>
            )}
            {content && (
              <pre
                data-testid="skill-content"
                className="max-h-[520px] overflow-y-auto whitespace-pre-wrap rounded-lg bg-slate-900/60 p-4 font-mono text-xs leading-relaxed text-slate-300"
              >
                {content}
              </pre>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
