export interface TerraformFile {
  filename: string;
  content: string;
  threatName: string;
  severity: string;
}

export interface ThreatResults {
  text: string;
  terraformFiles: TerraformFile[];
}

export async function parseThreatStream(response: Response): Promise<ThreatResults> {
  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';
  let text = '';
  const terraformFiles: TerraformFile[] = [];

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      // UI Message Stream format: "data: {json}"
      if (!line.startsWith('data: ')) continue;
      const jsonStr = line.slice(6);
      if (!jsonStr.trim()) continue;

      try {
        const evt = JSON.parse(jsonStr);

        // Text delta
        if (evt.type === 'text' && evt.text) {
          text += evt.text;
        }

        // Tool call — extract Terraform from args
        if (evt.type === 'tool-call' && evt.toolName === 'generateTerraform' && evt.args) {
          const args = evt.args;
          if (!terraformFiles.some(f => f.filename === args.filename)) {
            terraformFiles.push({
              filename: args.filename,
              content: args.content,
              threatName: args.threatName,
              severity: args.severity,
            });
          }
        }

        // Tool result — also extract if present
        if (evt.type === 'tool-result' && evt.result?.filename) {
          if (!terraformFiles.some(f => f.filename === evt.result.filename)) {
            terraformFiles.push({
              filename: evt.result.filename,
              content: evt.result.content || '',
              threatName: evt.result.threatName || '',
              severity: evt.result.severity || 'HIGH',
            });
          }
        }
      } catch {
        // skip malformed JSON
      }
    }
  }

  return { text, terraformFiles };
}
