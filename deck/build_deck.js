// Strategy deck: node deck/build_deck.js (after `python -m deck.export_data`). Output: outputs/sp500_factor_ml.pptx
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("./apply_theme.js");
const D = require("./deck_data.json");

const OUT = path.join(__dirname, "..", "outputs", "sp500_factor_ml.pptx");
// Sober palette shared with the Streamlit app: navy dominates, gold marks the index, blue the model.
const HEX = { navy: "0F1E3D", ink: "1F2937", white: "FFFFFF", mist: "EEF2F7", slate: "64748B",
  blue: "2558A8", gold: "B7791F", green: "1F9D55", purple: "7C3AED", grid: "E5E7EB" };
const THEME = {
  name: "Factor ML", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: HEX.ink, lt1: HEX.white, dk2: HEX.navy, lt2: HEX.mist, accent1: HEX.blue, accent2: HEX.gold,
    accent3: HEX.green, accent4: HEX.purple, accent5: HEX.slate, accent6: "C2362B", hlink: HEX.blue, folHlink: HEX.purple },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5 in
pres.title = "S&P 500 factor ML portfolio";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const W = 13.33;
const M = D.summary.metrics;
const pct = (x, d = 1) => `${(x * 100).toFixed(d)}%`;

pres.defineSlideMaster({
  title: "Dark",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.2, w: 11.7, h: 1.8, fontSize: 40,
      bold: true, color: C.background1, valign: "bottom", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 4.2, w: 11.7, h: 1.6, fontSize: 18,
      color: C.background2, valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "Dark list",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 0.6, w: 11.7, h: 1.0, fontSize: 36,
      bold: true, color: C.background1, valign: "middle", align: "left", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "Content",
  background: { color: C.background1 },
  margin: [0.5, 0.6, 0.6, 0.6],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.4, w: 12.1, h: 0.9, fontSize: 30,
      bold: true, color: C.text2, valign: "middle", align: "left", margin: 0 }, text: "" } },
    { text: { text: "S&P 500 factor ML portfolio  |  github.com/dmp009/sp500-factor-ml-portfolio",
      options: { x: 0.6, y: 7.0, w: 9, h: 0.3, fontSize: 10, color: C.accent5, margin: 0 } } },
  ],
  slideNumber: { x: 12.3, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: HEX.slate, align: "right" },
});

const content = (section, title) => {
  const s = pres.addSlide({ masterName: "Content", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  return s;
};
const text = (s, t, o) => s.addText(t, { isTextBox: true, fontSize: 15, color: C.text1, margin: 0, valign: "top", ...o });
const card = (s, x, y, w, h, name) =>
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: C.background2 },
    line: { color: C.background2 }, objectName: name });
const chartText = { catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt",
  legendFontFace: "+mn-lt", titleFontFace: "+mn-lt", catAxisLabelColor: HEX.slate, valAxisLabelColor: HEX.slate,
  catAxisLabelFontSize: 11, valAxisLabelFontSize: 11, dataLabelFontSize: 11, dataLabelColor: HEX.ink,
  valGridLine: { color: HEX.grid, size: 0.75 }, catGridLine: { style: "none" } };

// 1. Title
pres.addSection({ title: "Opening" });
let s = pres.addSlide({ masterName: "Dark", sectionTitle: "Opening" });
s.addText("Can machine learning pick S&P 500 stocks that beat the index?", { placeholder: "title" });
s.addText("A LightGBM stock ranker tested without look-ahead from 2013 to 2026, explained with SHAP and "
  + "Fama-French, and rebuilt every month by GitHub Actions.", { placeholder: "body" });
s.addNotes("The project answers one question with a fair test, then keeps the portfolio running live.");

// 2. The answer
s = content("Opening", "Short answer: no, and the test shows why");
const stats = [
  [pct(M.model.cagr), "Model, a year net of costs", C.accent1],
  [pct(M.sp500tr.cagr), "S&P 500 total return, a year", C.accent2],
  [D.summary.ic.mean.toFixed(3), `Mean information coefficient (t = ${D.summary.ic.t.toFixed(1)})`, C.text2],
  [pct(D.attribution.alpha_annual), `Annual alpha after six factors (t = ${D.attribution.alpha_t.toFixed(1)})`, C.text2],
];
stats.forEach(([v, l, col], i) => {
  const x = 0.6 + i * 3.1;
  card(s, x, 1.7, 2.8, 2.4, `stat-${i}`);
  text(s, v, { x: x + 0.25, y: 1.95, w: 2.3, h: 1.1, fontSize: 44, bold: true, color: col, fontFace: "Cambria" });
  text(s, l, { x: x + 0.25, y: 3.1, w: 2.3, h: 0.8, fontSize: 14, color: C.accent5 });
});
text(s, [
  { text: "The model's ranking skill is indistinguishable from zero over 165 months.", options: { bullet: true, breakLine: true } },
  { text: "Its returns come from a market beta of 1.2 and a value tilt, which lagged a cap-weighted index led by a few very large growth companies.", options: { bullet: true, breakLine: true } },
  { text: "Parameters were frozen on 2010-2012 and not re-tuned after seeing the result.", options: { bullet: true } },
], { x: 0.6, y: 4.5, w: 12.1, h: 2.2, fontSize: 16, paraSpaceAfter: 8 });

// 3. Data and universe
pres.addSection({ title: "Method" });
s = content("Method", "Only information that was public at the time");
const sources = [
  ["Index membership", "Month-end S&P 500 members since 2010, including companies that later left (fja05680/sp500, Wikipedia)."],
  ["Prices", "Daily Yahoo Finance prices, dividends and splits, turned into monthly total returns."],
  ["Accounting", "SEC XBRL filings, each value used only from the date it reached EDGAR."],
  ["Risk factors", "Fama-French five factors and momentum from Kenneth French's data library."],
];
sources.forEach(([h, b], i) => {
  const y = 1.6 + i * 1.3;
  card(s, 0.6, y, 7.2, 1.1, `source-${i}`);
  text(s, h, { x: 0.85, y: y + 0.15, w: 6.8, h: 0.35, fontSize: 16, bold: true, color: C.text2 });
  text(s, b, { x: 0.85, y: y + 0.5, w: 6.8, h: 0.55, fontSize: 13, color: C.text1 });
});
const sv = D.summary;
[[String(sv.universe.securities), "securities were members at some point"],
  [String(sv.survivorship.n_missing), `of them (${pct(sv.survivorship.share_missing, 0)}) have no Yahoo price`],
  [`${pct(sv.coverage["2010-06"], 0)} → ${pct(sv.coverage["2026-10"])}`, "members priced, June 2010 to October 2026"],
].forEach(([v, l], i) => {
  const y = 1.6 + i * 1.75;
  text(s, v, { x: 8.4, y, w: 4.3, h: 0.8, fontSize: 36, bold: true, color: C.text2, fontFace: "Cambria" });
  text(s, l, { x: 8.4, y: y + 0.8, w: 4.3, h: 0.6, fontSize: 14, color: C.accent5 });
});

// 4. Model
s = content("Method", "A monthly ranking model trained only on the past");
const steps = [
  ["14 characteristics", "Momentum, reversal, volatility, beta, size, value, profitability, accruals, leverage, asset growth, sector; ranked 0-1 within the month"],
  ["LightGBM", "Learns next-month return relative to the median stock; retrained every month on months up to M-2"],
  ["Top 50 portfolio", "Equal weight, rebalanced monthly, 10 bps a side; compared with the index, equal weight and a factor rule"],
  ["Explain", "SHAP for each pick and month; Fama-French 5 + momentum regression with Newey-West errors"],
];
steps.forEach(([h, b], i) => {
  const x = 0.6 + i * 3.1;
  card(s, x, 1.8, 2.8, 3.6, `step-${i}`);
  s.addShape(pres.shapes.OVAL, { x: x + 0.25, y: 2.05, w: 0.6, h: 0.6, fill: { color: C.text2 }, line: { color: C.text2 }, objectName: `step-num-${i}` });
  text(s, String(i + 1), { x: x + 0.25, y: 2.05, w: 0.6, h: 0.6, fontSize: 18, bold: true, color: C.background1, align: "center", valign: "middle" });
  text(s, h, { x: x + 0.25, y: 2.9, w: 2.3, h: 0.45, fontSize: 18, bold: true, color: C.text2 });
  text(s, b, { x: x + 0.25, y: 3.4, w: 2.35, h: 1.9, fontSize: 14 });
});
text(s, "Hyper-parameters chosen once on 2010-2012 (validation IC -0.03) and frozen: 31 leaves, 100 stocks per leaf, 300 trees, learning rate 0.03.",
  { x: 0.6, y: 5.8, w: 12.1, h: 0.6, fontSize: 14, italic: true, color: C.accent5 });

// 5. Results
pres.addSection({ title: "Results" });
s = content("Results", "The index beat every rule-based portfolio after costs");
const g = D.growth;
const years = g.years.map((y, i) => (i === g.years.length - 1 ? "Oct 2026" : y));
const series = [["sp500tr", "S&P 500 TR", HEX.gold], ["model", "LightGBM model", HEX.blue],
  ["equal_weight", "Equal weight", HEX.purple], ["factor_rule", "Factor rule", HEX.green]];
s.addChart(pres.charts.LINE, series.map(([k, n]) => ({ name: n, labels: years, values: g[k] })), {
  x: 0.6, y: 1.5, w: 7.6, h: 5.2, ...chartText, chartColors: series.map((x) => x[2]), lineSize: 2, lineDataSymbol: "none",
  showTitle: true, title: "Growth of $1 since February 2013, net of costs", titleFontSize: 13, titleColor: HEX.ink,
  showLegend: true, legendPos: "b", legendFontSize: 11, valAxisLabelFormatCode: "$0.0", objectName: "growth-chart",
});
const row = (k, n) => [n, pct(M[k].cagr), pct(M[k].vol), M[k].sharpe.toFixed(2), pct(M[k].max_dd)];
const hdr = ["Strategy", "CAGR", "Vol", "Sharpe", "Max DD"].map((t) => ({ text: t, options: { bold: true, color: HEX.white, fill: { color: HEX.navy } } }));
s.addTable([hdr, row("model", "Model"), row("factor_rule", "Factor rule"), row("equal_weight", "Equal weight"),
  row("sp500tr", "S&P 500 TR").map((t) => ({ text: t, options: { bold: true } }))], {
  x: 8.5, y: 1.7, w: 4.2, colW: [1.3, 0.7, 0.7, 0.7, 0.8], fontSize: 12, fontFace: "Calibri", color: HEX.ink,
  border: { type: "solid", pt: 0.5, color: HEX.grid }, align: "left", valign: "middle", rowH: 0.42,
});
text(s, `Model turnover is ${pct(M.model.avg_turnover, 0)} a month, so costs take about 1.5% a year. The top decile beat the bottom decile by only ${(D.summary.ic.top_minus_bottom_decile_monthly * 100).toFixed(2)} pp a month.`,
  { x: 8.5, y: 4.5, w: 4.2, h: 1.6, fontSize: 14 });

// 6. Attribution
s = content("Results", "Its returns are market beta and value, not stock-picking skill");
const A = D.attribution;
const fac = [["mkt_rf", "Market"], ["hml", "Value"], ["smb", "Size (small)"], ["mom", "Momentum"],
  ["cma", "Investment"], ["rmw", "Profitability"]];
s.addChart(pres.charts.BAR, [{ name: "Loading", labels: fac.map((f) => `${f[1]} (t = ${A.t_values[f[0]].toFixed(1)})`),
  values: fac.map((f) => +A.betas[f[0]].toFixed(2)) }], {
  x: 0.6, y: 1.5, w: 7.4, h: 5.2, barDir: "bar", ...chartText, chartColors: [HEX.blue], showLegend: false,
  showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00", catAxisOrientation: "maxMin",
  catAxisLabelPos: "low", valAxisMinVal: -0.4, valAxisMaxVal: 1.4,
  showTitle: true, title: "Factor loadings of monthly excess return, 2013-2026", titleFontSize: 13, titleColor: HEX.ink,
  objectName: "loadings-chart",
});
card(s, 8.4, 1.7, 4.3, 3.4, "reading-card");
text(s, [
  { text: `Alpha ${pct(A.alpha_annual)} a year, t = ${A.alpha_t.toFixed(1)}: not significant.`, options: { bold: true, breakLine: true } },
  { text: " ", options: { breakLine: true } },
  { text: `A market beta of ${A.betas.mkt_rf.toFixed(2)} makes it a more volatile version of the market.`, options: { bullet: true, breakLine: true } },
  { text: `A significant value tilt (t = ${A.t_values.hml.toFixed(1)}), in a period when value lagged growth.`, options: { bullet: true, breakLine: true } },
  { text: `Six factors explain ${pct(A.r2, 0)} of its monthly variation (Newey-West, 6 lags).`, options: { bullet: true } },
], { x: 8.65, y: 1.95, w: 3.8, h: 3.0, fontSize: 15, paraSpaceAfter: 6 });

// 7. What drives the model
s = content("Results", "The model leans on short-term price signals");
s.addChart(pres.charts.BAR, [{ name: "Mean |SHAP|", labels: D.shap.map((r) => r.label), values: D.shap.map((r) => r.value) }], {
  x: 0.6, y: 1.5, w: 7.4, h: 5.2, barDir: "bar", ...chartText, chartColors: [HEX.navy], showLegend: false,
  showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00", catAxisOrientation: "maxMin",
  showTitle: true, title: "Average |SHAP| per stock, pp of predicted monthly return", titleFontSize: 13, titleColor: HEX.ink,
  objectName: "shap-chart",
});
card(s, 8.4, 1.7, 4.3, 3.6, "shap-card");
text(s, [
  { text: "Last month's return, sector and 6-1 month momentum move the predictions most.", options: { bullet: true, breakLine: true } },
  { text: "The SHAP values of each stock add up to its score, so every pick in the app comes with its two largest reasons.", options: { bullet: true, breakLine: true } },
  { text: "Importance drifts over time; the app tracks it month by month.", options: { bullet: true } },
], { x: 8.65, y: 1.95, w: 3.8, h: 3.2, fontSize: 15, paraSpaceAfter: 8 });

// 8. Automation
pres.addSection({ title: "Operations" });
s = content("Operations", "Every month it runs itself, and says so when it can't");
const flow = ["Monthly schedule", "Refresh sources", "Five quality gates", "Retrain and rank", "Commit snapshot, app redeploys"];
flow.forEach((t, i) => {
  const x = 0.6 + i * 2.48;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.7, w: 2.2, h: 1.1, rectRadius: 0.08,
    fill: { color: i === 2 ? C.text2 : C.background2 }, line: { color: i === 2 ? C.text2 : C.background2 }, objectName: `flow-${i}` });
  text(s, t, { x: x + 0.15, y: 1.7, w: 1.9, h: 1.1, fontSize: 14, bold: true, align: "center", valign: "middle",
    color: i === 2 ? C.background1 : C.text2 });
  if (i < flow.length - 1) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + 2.23, y: 2.12, w: 0.22, h: 0.26,
    fill: { color: C.accent5 }, line: { color: C.accent5 }, objectName: `arrow-${i}` });
});
const gates = D.summary.gates.map(([n, ok, detail]) => [n[0].toUpperCase() + n.slice(1).replace(/_/g, " "), ok ? "Pass" : "Fail", detail]);
s.addTable([["Gate", "Last run", "Check"].map((t) => ({ text: t, options: { bold: true, color: HEX.white, fill: { color: HEX.navy } } })), ...gates], {
  x: 0.6, y: 3.3, w: 7.6, colW: [1.7, 0.9, 5.0], fontSize: 12, fontFace: "Calibri", color: HEX.ink, rowH: 0.4,
  border: { type: "solid", pt: 0.5, color: HEX.grid }, valign: "middle",
});
card(s, 8.6, 3.3, 4.1, 2.85, "alert-card");
text(s, [
  { text: "If any step fails", options: { bold: true, fontSize: 17, color: C.text2, breakLine: true } },
  { text: "Nothing is written. A GitHub issue labelled refresh-failed opens with the step, the error and the run link; the next good run closes it.", options: { breakLine: true } },
  { text: " ", options: { breakLine: true } },
  { text: "The live record is append-only: changing a past month raises an error.", options: {} },
], { x: 8.85, y: 3.5, w: 3.6, h: 2.5, fontSize: 14 });

// 9. Limits and next steps
pres.addSection({ title: "Close" });
s = pres.addSlide({ masterName: "Dark list", sectionTitle: "Close" });
s.addText("Limits and next steps", { placeholder: "title" });
const cols = [
  ["Limits", ["23% of past members have no free price, so early years cover fewer stocks and delisting losses are missing",
    "Free sources without a commercial vendor's corrections", "One market, one period, one model family, a flat cost"]],
  ["Next steps", ["Let the live record build up before judging the model again",
    "Sector-neutral and value-weighted variants", "A smaller-cap universe, where the literature finds more predictability"]],
];
cols.forEach(([h, items], i) => {
  const x = 0.8 + i * 6.0;
  text(s, h, { x, y: 2.0, w: 5.5, h: 0.5, fontSize: 22, bold: true, color: C.background1, fontFace: "Cambria" });
  text(s, items.map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < items.length - 1 } })),
    { x, y: 2.7, w: 5.5, h: 3.5, fontSize: 16, color: C.background2, paraSpaceAfter: 10 });
});

pres.writeFile({ fileName: OUT }).then(async () => {
  await applyTheme(OUT, THEME);
  console.log(`wrote ${OUT}`);
});
