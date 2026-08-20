// Generates due-date-pdf.csv from the source daily-probability table.
// Run with: node generate-due-date-pdf.js
// Re-run this whenever RAW_TABLE, SMOOTH_SIGMA, or the domain below change.

var fs = require('fs');
var path = require('path');

var RAW_TABLE = [
  // [week, day, daily probability %]
  // Source: TODO — add citation for this table.
  [35,0,0.1],[35,1,0.1],[35,2,0.1],[35,3,0.1],[35,4,0.1],[35,5,0.2],[35,6,0.2],
  [36,0,0.2],[36,1,0.3],[36,2,0.3],[36,3,0.4],[36,4,0.5],[36,5,0.5],[36,6,0.6],
  [37,0,0.7],[37,1,0.8],[37,2,0.9],[37,3,1.0],[37,4,1.2],[37,5,1.3],[37,6,1.4],
  [38,0,1.6],[38,1,1.7],[38,2,1.9],[38,3,2.1],[38,4,2.2],[38,5,2.4],[38,6,2.5],
  [39,0,2.7],[39,1,2.8],[39,2,2.9],[39,3,3.1],[39,4,3.2],[39,5,3.2],[39,6,3.3],
  [40,0,3.4],[40,1,3.4],[40,2,3.4],[40,3,3.4],[40,4,3.4],[40,5,3.3],[40,6,3.2],
  [41,0,3.2],[41,1,3.1],[41,2,2.9],[41,3,2.8],[41,4,2.7],[41,5,2.5],[41,6,2.4],
  [42,0,2.2],[42,1,2.1],[42,2,1.9],[42,3,1.7],[42,4,1.6],[42,5,1.4]
];

// The 1dp values sum to ~100.6%, not exactly 100% — rescale so the table
// integrates to 1 before it's treated as a density.
var rawDays = RAW_TABLE.map(function(r){ return r[0]*7 + r[1]; });
var rawProbs = RAW_TABLE.map(function(r){ return r[2]/100; });
var rawSum = rawProbs.reduce(function(a,b){ return a+b; }, 0);
rawProbs = rawProbs.map(function(p){ return p/rawSum; });

// Gaussian-kernel smoothing: treat each day as a point mass and convolve
// with sigma = 3.5 days, turning the 1dp-quantised table into a continuous
// density. Wider than the minimum needed to remove the rounding "steps"
// (which only needed ~1.3) — the extra width blends the seam between the
// real data (which ends at 42+5) and the extrapolated tail beyond it, which
// otherwise showed up as a visible kink/shoulder on the right side.
var SMOOTH_SIGMA = 3.5;
function smoothedPdf(x){
  var sum = 0;
  for(var i=0;i<rawDays.length;i++){
    var z = (x - rawDays[i]) / SMOOTH_SIGMA;
    sum += rawProbs[i] * Math.exp(-0.5*z*z);
  }
  return sum / (SMOOTH_SIGMA*Math.sqrt(2*Math.PI));
}

// Display range: 35+0 to 44+2. With the wider smoothing above, the curve
// needs eleven extra days past the table's last entry (42+5) to taper down
// to ~0.01% of its peak height — genuinely flat against the axis — rather
// than stopping at a visible height partway down.
var DISPLAY_MIN = rawDays[0], DISPLAY_MAX = rawDays[rawDays.length-1] + 11;

// Calculation range: widened a week earlier than the display range, so the
// (small but nonzero) probability the smoothed curve implies exists before
// 35+0 isn't just truncated out of the median/mode calculation.
var DOMAIN_MIN = DISPLAY_MIN - 7, DOMAIN_MAX = DISPLAY_MAX;

var STEP = 0.25; // days between rows
var rows = [];
var cum = 0, prevPdf = null;
for(var day = DOMAIN_MIN; day <= DOMAIN_MAX + 1e-9; day += STEP){
  var pdf = smoothedPdf(day);
  if(prevPdf !== null) cum += (pdf + prevPdf) / 2 * STEP;
  rows.push([day, pdf, cum]);
  prevPdf = pdf;
}
var total = rows[rows.length-1][2];
rows.forEach(function(r){ r[2] = r[2] / total; });

var lines = ['day,pdf,cdf'];
rows.forEach(function(r){
  lines.push(r[0].toFixed(2) + ',' + r[1].toFixed(6) + ',' + r[2].toFixed(6));
});

var outPath = path.join(__dirname, 'due-date-pdf.csv');
fs.writeFileSync(outPath, lines.join('\n') + '\n');
console.log('wrote', rows.length, 'rows to', outPath);
