const hamBurger = document.querySelector(".toggle-btn");

hamBurger.addEventListener("click", function () {
  document.querySelector("#sidebar").classList.toggle("expand");
});

document.addEventListener('DOMContentLoaded', function() {
  const table = document.querySelector('.table');
  
  // Add hover effect
  table.addEventListener('mouseover', function(event) {
      const cell = event.target.closest('td');
      if (cell) {
          const row = cell.parentElement;
          row.classList.add('highlight');
      }
  });

  // Remove hover effect
  table.addEventListener('mouseout', function(event) {
      const cell = event.target.closest('td');
      if (cell) {
          const row = cell.parentElement;
          row.classList.remove('highlight');
      }
  });

  // Existing code for adding rows
  document.getElementById('addRowIcon').addEventListener('click', function() {
      const newRow = document.createElement('tr');
      newRow.innerHTML = `
          <td><input type="text" class="form-control" placeholder="Enter name"></td>
          <td>
              <select class="form-select btn btn-white p-2 dropdown-toggle" aria-haspopup="true" aria-expanded="false">
                  <option value="option1">Text</option>
                  <option value="option2">Number</option>
                  <option value="option3">Integra</option>
                  <option value="option3">Float</option>
                  <option value="option3">Float</option>
              </select>
          </td>
          <td>
              <div>
                  <input type="checkbox" id="checkbox1">
              </div>
          </td>
          <td><input type="text" class="form-control" placeholder="Enter size"></td>
          <td>
              <select class="form-select btn btn-white p-2 dropdown-toggle" aria-haspopup="true" aria-expanded="false">
                  <option value="option1">Text</option>
                  <option value="option2">Number</option>
                  <option value="option3">Integra</option>
                  <option value="option3">Float</option>
                  <option value="option3">Float</option>
              </select>
          </td>
          <td class="text-center align-middle"><a>
              <i class="bi bi-trash remove-icon bg-danger p-2 "></i>
          </a></td> 
      `;

      document.getElementById('tableBody').appendChild(newRow);

      newRow.querySelector('.remove-icon').addEventListener('click', function() {
          newRow.remove();
      });
  });
});

  