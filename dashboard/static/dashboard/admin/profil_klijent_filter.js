'use strict';
(function () {
    function updateDomovi(klijentId) {
        var fromSelect = document.getElementById('id_upravljani_domovi_from');
        var toSelect = document.getElementById('id_upravljani_domovi_to');
        if (!fromSelect) return;

        if (!klijentId) {
            // Clear available list, keep chosen list intact
            while (fromSelect.options.length > 0) {
                fromSelect.remove(0);
            }
            return;
        }

        fetch('/dashboard/admin/domovi-po-klijentu/' + klijentId + '/')
            .then(function (response) { return response.json(); })
            .then(function (data) {
                // Collect IDs already in chosen list
                var chosenIds = new Set();
                if (toSelect) {
                    for (var i = 0; i < toSelect.options.length; i++) {
                        chosenIds.add(toSelect.options[i].value);
                    }
                }

                // Rebuild available list with domovi from this klijent that aren't chosen
                while (fromSelect.options.length > 0) {
                    fromSelect.remove(0);
                }
                data.domovi.forEach(function (dom) {
                    if (!chosenIds.has(String(dom.id))) {
                        var opt = document.createElement('option');
                        opt.value = dom.id;
                        opt.text = dom.naziv;
                        fromSelect.add(opt);
                    }
                });

                // Remove any chosen options that don't belong to this klijent
                if (toSelect) {
                    var validIds = new Set(data.domovi.map(function (d) { return String(d.id); }));
                    var toRemove = [];
                    for (var j = 0; j < toSelect.options.length; j++) {
                        if (!validIds.has(toSelect.options[j].value)) {
                            toRemove.push(toSelect.options[j]);
                        }
                    }
                    toRemove.forEach(function (opt) { toSelect.removeChild(opt); });
                }
            });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var klijentSelect = document.getElementById('id_klijent');
        if (!klijentSelect) return;

        klijentSelect.addEventListener('change', function () {
            updateDomovi(this.value);
        });

        // On page load, filter based on current value (edit form)
        if (klijentSelect.value) {
            updateDomovi(klijentSelect.value);
        }
    });
})();
