(function () {
  var inp = document.getElementById('collatz-input');
  var btn = document.getElementById('collatz-run');
  var out = document.getElementById('collatz-result');

  function trace(n) {
    var seq = [n], cur = n, maxVal = n, steps = 0;
    while (cur !== 1 && steps < 100000) {
      cur = cur % 2 === 0 ? cur / 2 : 3 * cur + 1;
      seq.push(cur);
      if (cur > maxVal) maxVal = cur;
      steps++;
    }
    return { seq: seq, steps: steps, maxVal: maxVal, converged: cur === 1 };
  }

  function run() {
    var n = parseInt(inp.value, 10);
    if (!n || n < 1 || !Number.isFinite(n)) {
      out.textContent = 'Please enter a positive integer.';
      out.style.display = 'block';
      return;
    }
    var r = trace(n);
    var preview = r.seq.length <= 20
      ? r.seq.join(' -> ')
      : r.seq.slice(0, 10).join(' -> ') + ' ... ' + r.seq.slice(-5).join(' -> ');
    out.textContent = [
      'Starting value : ' + n.toLocaleString(),
      'Stopping time  : ' + r.steps + ' steps',
      'Peak value     : ' + r.maxVal.toLocaleString(),
      'Converged to 1 : ' + (r.converged ? 'yes' : 'limit reached (>100k steps)'),
      '',
      'Sequence (' + r.seq.length + ' values):',
      preview
    ].join('\n');
    out.style.display = 'block';
  }

  btn.addEventListener('click', run);
  inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') run(); });
}());
