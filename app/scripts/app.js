document.addEventListener('DOMContentLoaded', async () => {
  const client = await app.initialized();

  const ticket = await client.data.get('ticket');

  document.getElementById('status').innerText =
    `Ticket #${ticket.ticket.id} loaded`;
});
