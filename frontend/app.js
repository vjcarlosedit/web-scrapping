// API base URL
const API_BASE = '/api';

// State
let currentChart = null;
let products = [];

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadProducts();
});

// Load statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();
        
        document.getElementById('totalProducts').textContent = data.total_products || 0;
        document.getElementById('totalRecords').textContent = data.total_price_records || 0;
        document.getElementById('checkedToday').textContent = data.checked_last_24h || 0;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load products
async function loadProducts() {
    try {
        const response = await fetch(`${API_BASE}/products`);
        products = await response.json();
        
        displayProducts(products);
    } catch (error) {
        console.error('Error loading products:', error);
        document.getElementById('productsList').innerHTML = 
            '<div class="loading">Error al cargar productos</div>';
    }
}

// Display products
function displayProducts(products) {
    const container = document.getElementById('productsList');
    
    if (products.length === 0) {
        container.innerHTML = '<div class="loading">No hay productos. ¡Añade uno para comenzar!</div>';
        return;
    }
    
    container.innerHTML = products.map(product => `
        <div class="product-card">
            ${product.image_url 
                ? `<img src="${product.image_url}" alt="${product.name}" class="product-image">`
                : '<div class="product-image placeholder">📦</div>'
            }
            <div class="product-info">
                <h3 class="product-name">${product.name}</h3>
                <span class="product-platform platform-${product.platform}">
                    ${product.platform === 'amazon' ? 'Amazon' : 'Mercado Libre'}
                </span>
                <div class="product-price">
                    ${product.current_price 
                        ? `${formatPrice(product.current_price, product.currency)}`
                        : 'Sin precio'
                    }
                </div>
                <div class="product-meta">
                    ${product.last_checked 
                        ? `Última actualización: ${formatDate(product.last_checked)}`
                        : 'No actualizado'
                    }
                </div>
                <div class="product-actions">
                    <button onclick="viewHistory(${product.id})" class="btn btn-primary btn-small">
                        📈 Ver Historial
                    </button>
                    <button onclick="updateProduct(${product.id})" class="btn btn-secondary btn-small">
                        🔄
                    </button>
                    <button onclick="deleteProduct(${product.id})" class="btn btn-danger btn-small">
                        🗑️
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

// Add product
async function addProduct() {
    const urlInput = document.getElementById('productUrl');
    const url = urlInput.value.trim();
    const messageDiv = document.getElementById('addProductMessage');
    
    if (!url) {
        showMessage('Por favor ingresa una URL', 'error');
        return;
    }
    
    // Validate URL
    if (!url.includes('amazon') && !url.includes('mercadolibre') && !url.includes('mercadolivre')) {
        showMessage('URL no soportada. Solo se acepta Amazon o Mercado Libre', 'error');
        return;
    }
    
    try {
        messageDiv.textContent = 'Añadiendo producto...';
        messageDiv.className = 'message';
        messageDiv.style.display = 'block';
        
        const response = await fetch(`${API_BASE}/products`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url })
        });
        
        if (response.ok) {
            const product = await response.json();
            showMessage(`✓ Producto añadido: ${product.name}`, 'success');
            urlInput.value = '';
            loadProducts();
            loadStats();
        } else {
            const error = await response.json();
            showMessage(`Error: ${error.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error adding product:', error);
        showMessage('Error al añadir producto. Intenta de nuevo.', 'error');
    }
}

// Update single product
async function updateProduct(productId) {
    try {
        const response = await fetch(`${API_BASE}/scrape/product/${productId}`, {
            method: 'POST'
        });
        
        if (response.ok) {
            showMessage('✓ Producto actualizado', 'success');
            loadProducts();
            loadStats();
        } else {
            showMessage('Error al actualizar producto', 'error');
        }
    } catch (error) {
        console.error('Error updating product:', error);
        showMessage('Error al actualizar producto', 'error');
    }
}

// Delete product
async function deleteProduct(productId) {
    if (!confirm('¿Estás seguro de que quieres eliminar este producto?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/products/${productId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showMessage('✓ Producto eliminado', 'success');
            loadProducts();
            loadStats();
        } else {
            showMessage('Error al eliminar producto', 'error');
        }
    } catch (error) {
        console.error('Error deleting product:', error);
        showMessage('Error al eliminar producto', 'error');
    }
}

// Scrape all products
async function scrapeAll() {
    if (!confirm('¿Actualizar precios de todos los productos? Esto puede tomar unos minutos.')) {
        return;
    }
    
    try {
        showMessage('Actualizando todos los productos...', 'success');
        
        const response = await fetch(`${API_BASE}/scrape/run`, {
            method: 'POST'
        });
        
        if (response.ok) {
            const result = await response.json();
            showMessage(
                `✓ Actualización completa: ${result.results.success}/${result.results.total} exitosos`,
                'success'
            );
            loadProducts();
            loadStats();
        } else {
            showMessage('Error al actualizar productos', 'error');
        }
    } catch (error) {
        console.error('Error scraping all:', error);
        showMessage('Error al actualizar productos', 'error');
    }
}

// View price history
async function viewHistory(productId) {
    try {
        // Get product info
        const productResponse = await fetch(`${API_BASE}/products/${productId}`);
        const product = await productResponse.json();
        
        // Get price history
        const historyResponse = await fetch(`${API_BASE}/products/${productId}/history?days=30`);
        const history = await historyResponse.json();
        
        // Get statistics
        const statsResponse = await fetch(`${API_BASE}/products/${productId}/stats?days=30`);
        const stats = await statsResponse.json();
        
        // Show modal
        showHistoryModal(product, history, stats);
    } catch (error) {
        console.error('Error loading history:', error);
        showMessage('Error al cargar historial', 'error');
    }
}

// Show history modal
function showHistoryModal(product, history, stats) {
    const modal = document.getElementById('historyModal');
    const title = document.getElementById('modalTitle');
    
    title.textContent = `Historial: ${product.name}`;
    
    // Display stats
    displayStats(stats, product.currency);
    
    // Create chart
    createPriceChart(history, product.currency);
    
    modal.classList.add('show');
}

// Display statistics
function displayStats(stats, currency) {
    const container = document.getElementById('priceStats');
    
    container.innerHTML = `
        <div class="stat-item">
            <div class="stat-item-label">Precio Actual</div>
            <div class="stat-item-value">${formatPrice(stats.current_price, currency)}</div>
        </div>
        <div class="stat-item">
            <div class="stat-item-label">Precio Mínimo</div>
            <div class="stat-item-value">${formatPrice(stats.min_price, currency)}</div>
        </div>
        <div class="stat-item">
            <div class="stat-item-label">Precio Máximo</div>
            <div class="stat-item-value">${formatPrice(stats.max_price, currency)}</div>
        </div>
        <div class="stat-item">
            <div class="stat-item-label">Precio Promedio</div>
            <div class="stat-item-value">${formatPrice(stats.avg_price, currency)}</div>
        </div>
    `;
}

// Create price chart
function createPriceChart(history, currency) {
    const canvas = document.getElementById('priceChart');
    const ctx = canvas.getContext('2d');
    
    // Destroy previous chart
    if (currentChart) {
        currentChart.destroy();
    }
    
    // Reverse history to show oldest first
    const sortedHistory = [...history].reverse();
    
    // Prepare data
    const labels = sortedHistory.map(entry => formatDate(entry.scraped_at));
    const prices = sortedHistory.map(entry => entry.price);
    
    // Create chart
    currentChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: `Precio (${currency})`,
                data: prices,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 4,
                pointHoverRadius: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Precio: ${formatPrice(context.parsed.y, currency)}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(value) {
                            return formatPrice(value, currency);
                        }
                    }
                }
            }
        }
    });
}

// Close modal
function closeModal() {
    const modal = document.getElementById('historyModal');
    modal.classList.remove('show');
    
    if (currentChart) {
        currentChart.destroy();
        currentChart = null;
    }
}

// Show message
function showMessage(message, type) {
    const messageDiv = document.getElementById('addProductMessage');
    messageDiv.textContent = message;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';
    
    setTimeout(() => {
        messageDiv.style.display = 'none';
    }, 5000);
}

// Format price
function formatPrice(price, currency = 'USD') {
    if (price === null || price === undefined) return 'N/A';
    
    const currencySymbols = {
        'USD': '$',
        'MXN': '$',
        'ARS': '$',
        'BRL': 'R$',
        'EUR': '€',
        'GBP': '£'
    };
    
    const symbol = currencySymbols[currency] || currency;
    return `${symbol}${price.toFixed(2)}`;
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Ahora';
    if (diffMins < 60) return `Hace ${diffMins} min`;
    if (diffHours < 24) return `Hace ${diffHours}h`;
    if (diffDays < 7) return `Hace ${diffDays}d`;
    
    return date.toLocaleDateString('es-ES', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('historyModal');
    if (event.target === modal) {
        closeModal();
    }
}

// Allow Enter key to add product
document.getElementById('productUrl')?.addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        addProduct();
    }
});

