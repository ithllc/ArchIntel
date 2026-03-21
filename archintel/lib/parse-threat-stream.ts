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
      if (!line.trim()) continue;

      if (line.startsWith('0:')) {
        try {
          const chunk = JSON.parse(line.slice(2));
          text += chunk;
        } catch {
          // skip malformed
        }
      }

      if (line.startsWith('a:')) {
        try {
          const toolResults = JSON.parse(line.slice(2));
          for (const result of toolResults) {
            if (result.type === 'tool-result' && result.result?.filename) {
              terraformFiles.push({
                filename: result.result.filename,
                content: result.result.content || '',
                threatName: result.result.threatName || '',
                severity: result.result.severity || 'HIGH',
              });
            }
          }
        } catch {
          // skip
        }
      }

      if (line.startsWith('9:')) {
        try {
          const toolCall = JSON.parse(line.slice(2));
          if (toolCall.toolName === 'generateTerraform' && toolCall.args) {
            const args = toolCall.args;
            if (!terraformFiles.some(f => f.filename === args.filename)) {
              terraformFiles.push({
                filename: args.filename,
                content: args.content,
                threatName: args.threatName,
                severity: args.severity,
              });
            }
          }
        } catch {
          // skip
        }
      }
    }
  }

  return { text, terraformFiles };
}
