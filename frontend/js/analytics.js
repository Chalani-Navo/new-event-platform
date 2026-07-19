const ANALYTICS_API_URL =
    "http:/analytics-api/api/v1/analytics";

function getSessionId() {
    let sessionId = sessionStorage.getItem("newEventSessionId");

    if (!sessionId) {
        sessionId =
            "session-" +
            Date.now() +
            "-" +
            Math.random().toString(36).substring(2, 10);

        sessionStorage.setItem("newEventSessionId", sessionId);
    }

    return sessionId;
}

function getDeviceType() {
    const width = window.innerWidth;

    if (width < 768) {
        return "mobile";
    }

    if (width < 1024) {
        return "tablet";
    }

    return "desktop";
}

async function sendAnalytics(
    eventType,
    sectionName = "",
    trackName = ""
) {
    const payload = {
        sessionId: getSessionId(),
        eventType: eventType,
        sectionName: sectionName,
        trackName: trackName,
        pagePath: window.location.pathname,
        deviceType: getDeviceType()
    };

    try {
        const response = await fetch(ANALYTICS_API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            console.error(
                "Analytics request failed:",
                response.status
            );
        }
    } catch (error) {
        console.error(
            "Unable to send analytics event:",
            error
        );
    }
}

document.addEventListener("DOMContentLoaded", function () {
    sendAnalytics("SECTION_VIEW", "home");

    const learnMoreButton = document.querySelector(
        'a[href="#overview"]'
    );

    if (learnMoreButton) {
        learnMoreButton.addEventListener("click", function () {
            sendAnalytics(
                "PROGRAM_TRACK_CLICK",
                "overview",
                "general-event-information"
            );
        });
    }

    const registerLinks = document.querySelectorAll(
        'a[href="#register"]'
    );

    registerLinks.forEach(function (registerLink) {
        registerLink.addEventListener("click", function () {
            sendAnalytics(
                "REGISTRATION_STARTED",
                "register"
            );
        });
    });

    const registrationForm = document.querySelector(
        "#register form"
    );

    if (registrationForm) {
        registrationForm.addEventListener(
            "submit",
            function () {
                sendAnalytics(
                    "REGISTRATION_SUBMITTED",
                    "register"
                );
            }
        );
    }

    const programLinks = document.querySelectorAll(
        '#program a[data-toggle="tab"]'
    );

    programLinks.forEach(function (programLink) {
        programLink.addEventListener("click", function () {
            const trackName =
                programLink.textContent.trim();

            sendAnalytics(
                "PROGRAM_TRACK_CLICK",
                "program",
                trackName
            );
        });
    });
});