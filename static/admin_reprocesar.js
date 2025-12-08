// Estado global
let todosLosViajes = [];
let viajesFiltrados = [];
let viajesSeleccionados = new Set();
let modoReprocesarTemp = { viajes: [], modo: 'desde_cero' };

// Cargar viajes al iniciar
document.addEventListener('DOMContentLoaded', () => {
    cargarViajes();
    cargarTiposError();
    cargarColaReprocesamiento();
});

async function cargarViajes() {
    try {
        const response = await fetch('/api/viajes-fallidos');
        const data = await response.json();

        if (data.success) {
            todosLosViajes = data.viajes;
            viajesFiltrados = [...todosLosViajes];
            renderizarTabla();
            actualizarContadores();
        }
    } catch (error) {
        console.error('Error cargando viajes:', error);
        mostrarAlerta('error', 'Error cargando viajes fallidos');
    }
}

async function cargarTiposError() {
    const erroresUnicos = new Set();
    todosLosViajes.forEach(v => erroresUnicos.add(v.motivo_fallo));

    const select = document.getElementById('errorFilter');
    erroresUnicos.forEach(error => {
        if (error) {
            const option = document.createElement('option');
            option.value = error;
            option.textContent = error;
            select.appendChild(option);
        }
    });
}

function renderizarTabla() {
    const tbody = document.getElementById('viajesBody');

    if (viajesFiltrados.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="10" class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <div>No hay viajes fallidos que mostrar</div>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = viajesFiltrados.map(viaje => {
        const intentos = viaje.num_intentos || 0;
        const intentosClass = intentos >= 5 ? 'attempts-high' : '';
        const enCola = viaje.en_cola;

        return `
            <tr>
                <td><input type="checkbox" class="viaje-checkbox" data-prefactura="${viaje.prefactura}" ${enCola ? 'disabled' : ''} onchange="toggleViaje('${viaje.prefactura}')"></td>
                <td>
                    <span class="${intentosClass} attempts-link" onclick="verHistorial('${viaje.prefactura}')">
                        ${intentos}
                    </span>
                </td>
                <td>${viaje.prefactura}</td>
                <td>${viaje.fecha_viaje}</td>
                <td>${viaje.placa_tractor}</td>
                <td>${viaje.placa_remolque}</td>
                <td>${viaje.determinante}</td>
                <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis;">${viaje.motivo_fallo}</td>
                <td>${viaje.timestamp}</td>
                <td>
                    <div class="actions-cell">
                        ${enCola ?
                            '<span class="badge badge-queue">⏳ En cola</span>' :
                            `
                            <button class="btn btn-edit" onclick="editarViaje('${viaje.prefactura}')">Editar</button>
                            <button class="btn btn-reprocess" onclick="reprocesarIndividual('${viaje.prefactura}')">Reprocesar</button>
                            <button class="btn btn-delete" onclick="eliminarViaje('${viaje.prefactura}')">Eliminar</button>
                            `
                        }
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function aplicarFiltros() {
    const busqueda = document.getElementById('searchInput').value.toLowerCase();
    const campoBusqueda = document.getElementById('searchField').value;
    const errorFiltro = document.getElementById('errorFilter').value;

    viajesFiltrados = todosLosViajes.filter(viaje => {
        let matchBusqueda = true;
        if (busqueda) {
            switch (campoBusqueda) {
                case 'todo':
                    matchBusqueda =
                        viaje.prefactura.toLowerCase().includes(busqueda) ||
                        viaje.placa_tractor.toLowerCase().includes(busqueda) ||
                        viaje.placa_remolque.toLowerCase().includes(busqueda) ||
                        viaje.determinante.toLowerCase().includes(busqueda);
                    break;
                case 'prefactura':
                    matchBusqueda = viaje.prefactura.toLowerCase().includes(busqueda);
                    break;
                case 'placa_tractor':
                    matchBusqueda = viaje.placa_tractor.toLowerCase().includes(busqueda);
                    break;
                case 'placa_remolque':
                    matchBusqueda = viaje.placa_remolque.toLowerCase().includes(busqueda);
                    break;
                case 'determinante':
                    matchBusqueda = viaje.determinante.toLowerCase().includes(busqueda);
                    break;
            }
        }

        const matchError = !errorFiltro || viaje.motivo_fallo === errorFiltro;

        return matchBusqueda && matchError;
    });

    // Aplicar filtros de fecha y etapa
    viajesFiltrados = aplicarFiltrosFecha(viajesFiltrados);
    viajesFiltrados = aplicarFiltrosEtapa(viajesFiltrados);

    renderizarTabla();
    actualizarContadores();

    // Limpiar selección
    viajesSeleccionados.clear();
    document.getElementById('selectAll').checked = false;
    actualizarBulkActions();
}

function actualizarContadores() {
    document.getElementById('totalCount').textContent = todosLosViajes.length;

    const filteredBadge = document.getElementById('filteredBadge');
    const filteredCount = document.getElementById('filteredCount');

    if (viajesFiltrados.length !== todosLosViajes.length) {
        filteredCount.textContent = viajesFiltrados.length;
        filteredBadge.style.display = 'inline-block';
    } else {
        filteredBadge.style.display = 'none';
    }
}

function toggleSelectAll() {
    const checked = document.getElementById('selectAll').checked;
    const checkboxes = document.querySelectorAll('.viaje-checkbox:not(:disabled)');

    viajesSeleccionados.clear();
    checkboxes.forEach(cb => {
        cb.checked = checked;
        if (checked) {
            viajesSeleccionados.add(cb.dataset.prefactura);
        }
    });

    actualizarBulkActions();
}

function toggleViaje(prefactura) {
    if (viajesSeleccionados.has(prefactura)) {
        viajesSeleccionados.delete(prefactura);
    } else {
        viajesSeleccionados.add(prefactura);
    }
    actualizarBulkActions();
}

function actualizarBulkActions() {
    const bulkActions = document.getElementById('bulkActions');
    const count = viajesSeleccionados.size;

    if (count > 0) {
        bulkActions.style.display = 'flex';
        document.getElementById('selectedCount').textContent = count;
    } else {
        bulkActions.style.display = 'none';
    }
}

async function verHistorial(prefactura) {
    try {
        const response = await fetch(`/api/viaje-historial/${prefactura}`);
        const data = await response.json();

        if (data.success) {
            document.getElementById('historialPrefactura').textContent = `Prefactura: ${prefactura}`;

            const contenido = document.getElementById('historialContenido');

            if (data.historial.intentos.length === 0) {
                contenido.innerHTML = '<p style="color: #a0aec0;">No hay historial de intentos</p>';
            } else {
                contenido.innerHTML = data.historial.intentos.map((intento, index) => `
                    <div class="history-item">
                        <div class="history-timestamp">Intento ${index + 1} - ${intento.timestamp}</div>
                        <div class="history-error">❌ ${intento.error}</div>
                        ${intento.tractor ? `<div style="font-size: 12px; color: #718096; margin-top: 4px;">Tractor: ${intento.tractor}</div>` : ''}
                    </div>
                `).join('');
            }

            abrirModal('modalHistorial');
        }
    } catch (error) {
        console.error('Error obteniendo historial:', error);
        mostrarAlerta('error', 'Error obteniendo historial del viaje');
    }
}

function editarViaje(prefactura) {
    const viaje = todosLosViajes.find(v => v.prefactura === prefactura);
    if (!viaje) return;

    document.getElementById('editarTitulo').textContent = `Editar Viaje - ${prefactura}`;
    document.getElementById('editPrefacturaOriginal').value = prefactura;
    document.getElementById('editPrefactura').value = viaje.prefactura;
    document.getElementById('editDeterminante').value = viaje.determinante;
    document.getElementById('editFechaViaje').value = viaje.fecha_viaje;
    document.getElementById('editTractor').value = viaje.placa_tractor;
    document.getElementById('editRemolque').value = viaje.placa_remolque;

    abrirModal('modalEditar');
}

async function guardarEdicion() {
    const prefacturaOriginal = document.getElementById('editPrefacturaOriginal').value;
    const prefactura = document.getElementById('editPrefactura').value;
    const determinante = document.getElementById('editDeterminante').value;
    const fecha_viaje = document.getElementById('editFechaViaje').value;
    const placa_tractor = document.getElementById('editTractor').value;
    const placa_remolque = document.getElementById('editRemolque').value;

    try {
        const response = await fetch(`/api/viajes-fallidos/${prefacturaOriginal}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prefactura,
                determinante,
                fecha_viaje,
                placa_tractor,
                placa_remolque
            })
        });

        const data = await response.json();

        if (data.success) {
            mostrarAlerta('success', 'Viaje actualizado exitosamente');
            cerrarModal('modalEditar');
            cargarViajes();
        } else {
            mostrarAlerta('error', data.mensaje);
        }
    } catch (error) {
        mostrarAlerta('error', 'Error actualizando viaje');
    }
}

function editarSeleccionados() {
    if (viajesSeleccionados.size === 0) return;

    document.getElementById('cantidadMasivo').textContent = viajesSeleccionados.size;
    document.getElementById('masivoDeterminante').value = '';
    document.getElementById('masivoTractor').value = '';
    document.getElementById('masivoRemolque').value = '';

    abrirModal('modalEditarMasivo');
}

async function aplicarEdicionMasiva() {
    const determinante = document.getElementById('masivoDeterminante').value.trim();
    const tractor = document.getElementById('masivoTractor').value.trim();
    const remolque = document.getElementById('masivoRemolque').value.trim();

    if (!determinante && !tractor && !remolque) {
        mostrarAlerta('error', 'Debes completar al menos un campo para aplicar cambios');
        return;
    }

    const cambios = {};
    if (determinante) cambios.determinante = determinante;
    if (tractor) cambios.placa_tractor = tractor;
    if (remolque) cambios.placa_remolque = remolque;

    try {
        const response = await fetch('/api/viajes-fallidos/edicion-masiva', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prefacturas: Array.from(viajesSeleccionados),
                cambios
            })
        });

        const data = await response.json();

        if (data.success) {
            mostrarAlerta('success', `${data.actualizados} viaje(s) actualizados`);
            cerrarModal('modalEditarMasivo');
            viajesSeleccionados.clear();
            actualizarBulkActions();
            cargarViajes();
        } else {
            mostrarAlerta('error', data.mensaje);
        }
    } catch (error) {
        mostrarAlerta('error', 'Error en edición masiva');
    }
}

function reprocesarIndividual(prefactura) {
    modoReprocesarTemp = {
        viajes: [prefactura],
        modo: 'desde_cero'
    };

    document.getElementById('modoReprocesarInfo').textContent = `Prefactura: ${prefactura}`;
    document.getElementById('modoDesdeCero').checked = true;
    abrirModal('modalModoReprocesar');
}

function reprocesarSeleccionados() {
    if (viajesSeleccionados.size === 0) return;

    if (viajesSeleccionados.size > 400) {
        if (!confirm(`⚠️ Vas a reprocesar ${viajesSeleccionados.size} viajes\n\nEsto agregará todos los viajes a la cola. El robot los procesará uno por uno. Puede tomar varias horas.\n\n¿Continuar?`)) {
            return;
        }
    }

    modoReprocesarTemp = {
        viajes: Array.from(viajesSeleccionados),
        modo: 'desde_cero'
    };

    document.getElementById('modoReprocesarInfo').textContent = `${viajesSeleccionados.size} viajes seleccionados`;
    document.getElementById('modoDesdeCero').checked = true;
    abrirModal('modalModoReprocesar');
}

async function confirmarReprocesar() {
    const modo = document.querySelector('input[name="modoReprocesar"]:checked').value;
    modoReprocesarTemp.modo = modo;

    try {
        const response = await fetch('/api/reprocesar-viajes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prefacturas: modoReprocesarTemp.viajes,
                modo: modo
            })
        });

        const data = await response.json();

        if (data.success) {
            mostrarAlerta('success', data.mensaje);
            cerrarModal('modalModoReprocesar');
            viajesSeleccionados.clear();
            actualizarBulkActions();
            cargarViajes();
        } else {
            mostrarAlerta('error', data.mensaje);
        }
    } catch (error) {
        mostrarAlerta('error', 'Error reprocesando viajes');
    }
}

async function eliminarViaje(prefactura) {
    if (!confirm(`¿Estás seguro de eliminar el viaje ${prefactura}?\n\nEsta acción no se puede deshacer.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/viajes-fallidos/${prefactura}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            mostrarAlerta('success', 'Viaje eliminado exitosamente');
            cargarViajes();
        } else {
            mostrarAlerta('error', data.mensaje);
        }
    } catch (error) {
        mostrarAlerta('error', 'Error eliminando viaje');
    }
}

async function eliminarSeleccionados() {
    if (viajesSeleccionados.size === 0) return;

    if (!confirm(`¿Estás seguro de eliminar ${viajesSeleccionados.size} viaje(s)?\n\nEsta acción no se puede deshacer.`)) {
        return;
    }

    try {
        const response = await fetch('/api/viajes-fallidos/eliminar-masivo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prefacturas: Array.from(viajesSeleccionados)
            })
        });

        const data = await response.json();

        if (data.success) {
            mostrarAlerta('success', `${data.eliminados} viaje(s) eliminados`);
            viajesSeleccionados.clear();
            actualizarBulkActions();
            cargarViajes();
        } else {
            mostrarAlerta('error', data.mensaje);
        }
    } catch (error) {
        mostrarAlerta('error', 'Error eliminando viajes');
    }
}

function abrirModal(modalId) {
    document.getElementById(modalId).style.display = 'flex';
}

function cerrarModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function mostrarAlerta(tipo, mensaje) {
    const container = document.getElementById('alertContainer');
    const alert = document.createElement('div');
    alert.className = `alert alert-${tipo}`;
    alert.textContent = mensaje;
    alert.style.display = 'block';

    container.innerHTML = '';
    container.appendChild(alert);

    setTimeout(() => {
        alert.style.display = 'none';
    }, 5000);
}

// === FUNCIONES DE COLA DE REPROCESAMIENTO ===

async function cargarColaReprocesamiento() {
    try {
        const response = await fetch('/api/cola-reprocesamiento');
        const data = await response.json();

        if (data.success) {
            const tbody = document.getElementById('colaBody');
            const countBadge = document.getElementById('colaCount');

            countBadge.textContent = `${data.total} viajes en cola`;

            if (data.cola.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No hay viajes en cola</td></tr>';
                return;
            }

            tbody.innerHTML = data.cola.map(viaje => {
                const estado = viaje.estado || 'PENDIENTE';
                const estadoClass = estado === 'PENDIENTE' ? 'badge-warning' : 'badge-info';

                return `
                    <tr>
                        <td><strong>${viaje.prefactura || 'N/A'}</strong></td>
                        <td>${viaje.determinante || 'N/A'}</td>
                        <td>${viaje.fecha_viaje || 'N/A'}</td>
                        <td>${viaje.placa_tractor || ''} / ${viaje.placa_remolque || ''}</td>
                        <td><span class="badge ${estadoClass}">${estado}</span></td>
                        <td>
                            <button class="btn btn-danger btn-sm" onclick="eliminarDeCola('${viaje.prefactura}')" title="Eliminar de cola">
                                🗑️ Eliminar
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
        }
    } catch (error) {
        console.error('Error cargando cola:', error);
    }
}

async function eliminarDeCola(prefactura) {
    if (!confirm(`¿Eliminar viaje ${prefactura} de la cola?`)) return;

    try {
        const response = await fetch(`/api/cola-reprocesamiento/${prefactura}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            mostrarAlerta('Viaje eliminado de la cola', 'success');
            cargarColaReprocesamiento();
        } else {
            mostrarAlerta('Error eliminando viaje: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        mostrarAlerta('Error eliminando viaje', 'error');
    }
}

// Agregar filtrado por fecha y etapa
function aplicarFiltrosFecha(viajes) {
    const fechaDesde = document.getElementById('fechaDesde').value;
    const fechaHasta = document.getElementById('fechaHasta').value;

    if (!fechaDesde && !fechaHasta) return viajes;

    return viajes.filter(viaje => {
        if (!viaje.timestamp_fallo) return true;

        const fechaFallo = new Date(viaje.timestamp_fallo);
        const fechaFalloStr = fechaFallo.toISOString().split('T')[0];

        if (fechaDesde && fechaFalloStr < fechaDesde) return false;
        if (fechaHasta && fechaFalloStr > fechaHasta) return false;

        return true;
    });
}

function aplicarFiltrosEtapa(viajes) {
    const filtroEtapa = document.getElementById('etapaFilter').value;
    if (!filtroEtapa) return viajes;

    return viajes.filter(viaje => {
        const motivo = (viaje.motivo_fallo || '').toUpperCase();
        return motivo.includes(filtroEtapa);
    });
}

// Recargar cola periódicamente
setInterval(cargarColaReprocesamiento, 30000); // Cada 30 segundos

// Cerrar modales al hacer clic fuera
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}