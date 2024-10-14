const loginButton = document.getElementById('login-button');
const fetchEventsButton = document.getElementById('fetch-events-button');
const fetchAvailabilitiesButton = document.getElementById('fetch-availabilities-button');
const eventsList = document.getElementById('events-list');
const availabilitiesList = document.getElementById('availabilities-list');
const fetchEmailsButton = document.getElementById('fetch-emails-button');
const fetchContactsButton = document.getElementById('fetch-contacts-button');
const sendEmailButton = document.getElementById('send-email-button');
const createEventButton = document.getElementById('create-event-button');
const emailsList = document.getElementById('emails-list');
const contactsList = document.getElementById('contacts-list');
const emailForm = document.getElementById('email-form');
const eventForm = document.getElementById('event-form');
const { DateTime } = luxon;
const openChatButton = document.getElementById('open-chat-button');
const chatContainer = document.getElementById('chat-container');
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendMessageButton = document.getElementById('send-message');

loginButton.addEventListener('click', () => {
  window.location.href = '/login';
});

fetchEventsButton.addEventListener('click', async () => {
  try {
    const response = await axios.get('/calendar_events');
    eventsList.innerHTML = '<h2>Your Upcoming Events:</h2>';
    response.data.forEach(event => {
      const eventElement = document.createElement('div');
      eventElement.classList.add('event-item');
      eventElement.innerHTML = `
        <strong>Summary:</strong> ${event.summary}<br>
        <strong>Start:</strong> ${event.start}<br>
        <strong>End:</strong> ${event.end}<br>
        <strong>Organizer:</strong> ${event.organizer || 'Not specified'}<br>
        <strong>Description:</strong> ${event.description}<br>
        <strong>Location:</strong> ${event.location}<br>
        <strong>Status:</strong> ${event.status}
      `;
      eventsList.appendChild(eventElement);
    });
  } catch (error) {
    console.error('Error fetching events:', error);
    eventsList.innerHTML = '<p>Error fetching events. Please try again.</p>';
  }
});

fetchAvailabilitiesButton.addEventListener('click', async () => {
  try {
    const response = await axios.get('/availabilities');
    availabilitiesList.innerHTML = '<h2>Your Availabilities:</h2>';
    response.data.forEach(availability => {
      const availabilityElement = document.createElement('div');
      availabilityElement.classList.add('availability-item');
      availabilityElement.innerHTML = `
        <strong>Start:</strong> ${availability.start}<br>
        <strong>End:</strong> ${availability.end}
      `;
      availabilitiesList.appendChild(availabilityElement);
    });
  } catch (error) {
    console.error('Error fetching availabilities:', error);
    availabilitiesList.innerHTML = '<p>Error fetching availabilities. Please try again.</p>';
  }
});

fetchEmailsButton.addEventListener('click', async () => {
  try {
    const response = await axios.get('/todays_emails');
    emailsList.innerHTML = '<h2>Today\'s Emails:</h2>';
    if (response.data.emails && response.data.emails.length > 0) {
      response.data.emails.forEach(email => {
        const emailElement = document.createElement('div');
        emailElement.classList.add('email-item');
        emailElement.innerHTML = `
          <strong>Subject:</strong> ${email.subject}<br>
          <strong>From:</strong> ${email.sender}<br>
          <strong>Date:</strong> ${email.date}<br>
          <strong>Received:</strong> ${email.internal_date}<br>
          <strong>Snippet:</strong> ${email.snippet}
        `;
        emailsList.appendChild(emailElement);
      });
    } else {
      emailsList.innerHTML += '<p>No emails found for today.</p>';
    }
    emailsList.innerHTML += `<p>Total results: ${response.data.total_results}</p>`;
    emailsList.innerHTML += `<p>Query used: ${response.data.query}</p>`;
  } catch (error) {
    console.error('Error fetching emails:', error);
    emailsList.innerHTML = '<p>Error fetching emails. Please try again.</p>';
  }
});

fetchContactsButton.addEventListener('click', async () => {
  try {
    const response = await axios.get('/contacts');
    contactsList.innerHTML = '<h2>Your Contacts:</h2>';
    response.data.forEach(contact => {
      const contactElement = document.createElement('div');
      contactElement.classList.add('contact-item');
      contactElement.textContent = contact;
      contactsList.appendChild(contactElement);
    });
  } catch (error) {
    console.error('Error fetching contacts:', error);
    contactsList.innerHTML = '<p>Error fetching contacts. Please try again.</p>';
  }
});

sendEmailButton.addEventListener('click', () => {
  emailForm.style.display = 'block';
});

createEventButton.addEventListener('click', () => {
  eventForm.style.display = 'block';
});

document.getElementById('send-email-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const to = document.getElementById('email-to').value;
  const subject = document.getElementById('email-subject').value;
  const body = document.getElementById('email-body').value;
  try {
    const response = await axios.post('/send_email', { to, subject, body });
    alert('Email sent successfully!');
    emailForm.style.display = 'none';
  } catch (error) {
    console.error('Error sending email:', error);
    alert('Error sending email. Please try again.');
  }
});

document.getElementById('create-event-form').addEventListener('submit', async (e) => {
  e.preventDefault();

  const summary = document.getElementById('event-summary').value.trim();
  let start = document.getElementById('event-start').value;
  let end = document.getElementById('event-end').value;
  const description = document.getElementById('event-description').value.trim();
  const location = document.getElementById('event-location').value.trim();

  const timeZone = DateTime.local().zoneName;

  // Convert to RFC3339 format
  start = DateTime.fromISO(start, { zone: timeZone }).toISO();
  end = DateTime.fromISO(end, { zone: timeZone }).toISO();

  if (DateTime.fromISO(start) >= DateTime.fromISO(end)) {
    alert('End time must be after start time.');
    return;
  }

  try {
    const response = await axios.post('/create_event', { summary, start, end, description, location, timeZone });
    alert('Event created successfully!');
    console.log('Event details:', response.data);
  } catch (error) {
    console.error('Error creating event:', error.response?.data || error.message);
    alert('Error creating event. Please check the console for details.');
  }
});

openChatButton.addEventListener('click', () => {
  chatContainer.style.display = 'flex';
});

sendMessageButton.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    sendMessage();
  }
});

function sendMessage() {
  const message = userInput.value.trim();
  if (message) {
    addMessageToChat('user', message);
    userInput.value = '';

    axios.post('/email_manager', { input: message })
      .then(response => {
        const aiResponses = response.data.response;
        aiResponses.forEach(response => {
          addMessageToChat('ai', response);
        });
      })
      .catch(error => {
        console.error('Error sending message:', error);
        addMessageToChat('ai', 'Sorry, an error occurred. Please try again.');
      });
  }
}

function addMessageToChat(sender, message) {
  const messageElement = document.createElement('div');
  messageElement.classList.add('message', `${sender}-message`);
  messageElement.textContent = message;
  chatMessages.appendChild(messageElement);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Check if user is logged in
axios.get('/check_login')
  .then(response => {
    if (response.data.logged_in) {
      loginButton.style.display = 'none';
      fetchEventsButton.style.display = 'inline-block';
      fetchAvailabilitiesButton.style.display = 'inline-block';
      fetchEmailsButton.style.display = 'inline-block';
      fetchContactsButton.style.display = 'inline-block';
      sendEmailButton.style.display = 'inline-block';
      createEventButton.style.display = 'inline-block';
      openChatButton.style.display = 'inline-block';  // Show the chat button when logged in
    }
  })
  .catch(error => console.error('Error checking login status:', error));

// Function to open the chat window
document.getElementById('open-chat-button').addEventListener('click', function () {
  document.getElementById('chat-container').style.display = 'flex';
});

// Function to close the chat window
document.getElementById('close-chat-button').addEventListener('click', function () {
  document.getElementById('chat-container').style.display = 'none';
});