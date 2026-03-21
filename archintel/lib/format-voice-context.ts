import type { ThreatResults } from './parse-threat-stream';
import type { CostResults } from './pipeline-types';

export function formatThreatSummaryForVoice(results: ThreatResults): string {
  // Extract top threats from the markdown — look for ### headings under STRIDE
  const lines = results.text.split('\n');
  const criticalThreats: string[] = [];
  let inCritical = false;

  for (const line of lines) {
    if (line.includes('Critical Threats') || line.includes('critical') || line.includes('HIGH')) {
      inCritical = true;
      continue;
    }
    if (inCritical && line.startsWith('###')) {
      inCritical = false;
    }
    if (inCritical && line.trim().startsWith('-') || inCritical && line.trim().startsWith('*') || inCritical && /^\d+\./.test(line.trim())) {
      criticalThreats.push(line.trim().replace(/^[-*\d.]+\s*/, ''));
      if (criticalThreats.length >= 5) break;
    }
  }

  const threatList = criticalThreats.length > 0
    ? criticalThreats.map((t, i) => `${i + 1}. ${t}`).join('\n')
    : 'See the Security tab for full threat details.';

  const tfList = results.terraformFiles.length > 0
    ? results.terraformFiles.map(tf => `- ${tf.filename}: fixes ${tf.threatName} (${tf.severity})`).join('\n')
    : 'No Terraform policies generated.';

  return `[SECURITY ANALYSIS COMPLETE] The automated STRIDE threat analysis has finished. Here are the key findings:

Top threats identified:
${threatList}

${results.terraformFiles.length} Terraform remediation policies generated:
${tfList}

Use this data to answer the user's specific questions about security threats, remediations, and Terraform policies. Refer them to the Security tab for full details and downloadable Terraform files.`;
}

export function formatCostSummaryForVoice(results: CostResults): string {
  const serviceLines = results.breakdown
    .filter(s => s.monthlyCost > 0)
    .sort((a, b) => b.monthlyCost - a.monthlyCost)
    .slice(0, 5)
    .map(s => `- ${s.name}: $${s.monthlyCost}/month`)
    .join('\n');

  return `[COST ANALYSIS COMPLETE] The automated cost estimation has finished. Here are the key findings:

Total Monthly Cost: $${results.totalMonthlyCost}
Annual Estimate: $${results.annualEstimate}

Top services by cost:
${serviceLines || 'No services with costs identified.'}

These are estimates based on default assumptions (730 compute hours/month, 100GB data). Use this data to answer the user's specific questions about costs, pricing, and optimization. Refer them to the Costs tab for the full breakdown.`;
}
