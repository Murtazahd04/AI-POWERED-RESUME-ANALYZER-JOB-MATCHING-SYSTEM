import { useEffect, useState } from "react";
import { apiErrorMessage } from "../api/client";
import { authApi, profileApi } from "../api/endpoints";
import { useAuth } from "../context/AuthContext";

const EMPTY_PASSWORD_FORM = {
  current_password: "",
  new_password: "",
  confirm_password: "",
};

function formatDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Unavailable" : date.toLocaleDateString();
}

export default function ProfilePage() {
  const { updateUser } = useAuth();
  const [profile, setProfile] = useState(null);
  const [profileForm, setProfileForm] = useState({ name: "", email: "" });
  const [profileLoading, setProfileLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [profileError, setProfileError] = useState("");
  const [profileSuccess, setProfileSuccess] = useState("");
  const [profileBusy, setProfileBusy] = useState(false);
  const [passwordForm, setPasswordForm] = useState(EMPTY_PASSWORD_FORM);
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState("");
  const [passwordBusy, setPasswordBusy] = useState(false);

  useEffect(() => {
    let active = true;
    setProfileLoading(true);
    setLoadError("");

    authApi.me()
      .then((data) => {
        if (!active) return;
        setProfile(data);
        setProfileForm({ name: data.name, email: data.email });
        updateUser(data);
      })
      .catch((err) => {
        if (active) setLoadError(apiErrorMessage(err, "Couldn't load your profile."));
      })
      .finally(() => {
        if (active) setProfileLoading(false);
      });

    return () => {
      active = false;
    };
  }, [reloadKey, updateUser]);

  const updateProfile = async (event) => {
    event.preventDefault();
    setProfileError("");
    setProfileSuccess("");

    const name = profileForm.name.trim();
    const email = profileForm.email.trim();
    if (name.length < 2) {
      setProfileError("Name must be at least 2 characters.");
      return;
    }

    setProfileBusy(true);
    try {
      const updatedProfile = await profileApi.update({ name, email });
      setProfile(updatedProfile);
      setProfileForm({ name: updatedProfile.name, email: updatedProfile.email });
      updateUser(updatedProfile);
      setProfileSuccess("Profile updated.");
    } catch (err) {
      setProfileError(apiErrorMessage(err, "Couldn't update your profile."));
    } finally {
      setProfileBusy(false);
    }
  };

  const changePassword = async (event) => {
    event.preventDefault();
    setPasswordError("");
    setPasswordSuccess("");

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordError("New password and confirmation do not match.");
      return;
    }
    if (
      passwordForm.new_password.length < 8
      || passwordForm.new_password.length > 72
      || !/[A-Za-z]/.test(passwordForm.new_password)
      || !/\d/.test(passwordForm.new_password)
    ) {
      setPasswordError("New password must be 8-72 characters and contain a letter and a number.");
      return;
    }

    setPasswordBusy(true);
    try {
      await profileApi.changePassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });
      setPasswordForm(EMPTY_PASSWORD_FORM);
      setPasswordSuccess("Password updated.");
    } catch (err) {
      setPasswordError(apiErrorMessage(err, "Couldn't change your password."));
    } finally {
      setPasswordBusy(false);
    }
  };

  if (profileLoading) {
    return (
      <div>
        <h1 className="page-title">Profile</h1>
        <p className="muted" role="status">Loading your profile...</p>
      </div>
    );
  }

  if (loadError) {
    return (
      <div>
        <h1 className="page-title">Profile</h1>
        <div className="auth-error" role="alert">{loadError}</div>
        <button className="btn-small" type="button" onClick={() => setReloadKey((key) => key + 1)}>
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="profile-page">
      <h1 className="page-title">My profile</h1>
      <p className="page-subtitle">Manage your account details and password.</p>

      <section className="profile-card" aria-labelledby="account-details-title">
        <h2 id="account-details-title">Account details</h2>
        <dl className="profile-meta">
          <div>
            <dt>Account type</dt>
            <dd>{profile.role}</dd>
          </div>
          <div>
            <dt>Member since</dt>
            <dd>{formatDate(profile.created_at)}</dd>
          </div>
        </dl>

        <form onSubmit={updateProfile}>
          {profileError && <div className="auth-error" role="alert">{profileError}</div>}
          {profileSuccess && <div className="auth-success" role="status">{profileSuccess}</div>}

          <div className="profile-form-grid">
            <label className="editor-field">
              <span>Full name</span>
              <input
                autoComplete="name"
                maxLength={80}
                minLength={2}
                required
                value={profileForm.name}
                onChange={(event) => setProfileForm({ ...profileForm, name: event.target.value })}
              />
            </label>
            <label className="editor-field">
              <span>Email address</span>
              <input
                autoComplete="email"
                maxLength={254}
                required
                type="email"
                value={profileForm.email}
                onChange={(event) => setProfileForm({ ...profileForm, email: event.target.value })}
              />
            </label>
          </div>
          <div className="profile-actions">
            <button className="btn-primary profile-submit" type="submit" disabled={profileBusy}>
              {profileBusy ? "Saving..." : "Save profile"}
            </button>
          </div>
        </form>
      </section>

      <section className="profile-card" aria-labelledby="change-password-title">
        <h2 id="change-password-title">Change password</h2>
        <p className="muted">Choose a password with at least 8 characters, including a letter and a number.</p>
        <form onSubmit={changePassword}>
          {passwordError && <div className="auth-error" role="alert">{passwordError}</div>}
          {passwordSuccess && <div className="auth-success" role="status">{passwordSuccess}</div>}

          <label className="editor-field">
            <span>Current password</span>
            <input
              autoComplete="current-password"
              required
              type="password"
              value={passwordForm.current_password}
              onChange={(event) => setPasswordForm({ ...passwordForm, current_password: event.target.value })}
            />
          </label>
          <div className="profile-form-grid">
            <label className="editor-field">
              <span>New password</span>
              <input
                autoComplete="new-password"
                maxLength={72}
                minLength={8}
                required
                type="password"
                value={passwordForm.new_password}
                onChange={(event) => setPasswordForm({ ...passwordForm, new_password: event.target.value })}
              />
            </label>
            <label className="editor-field">
              <span>Confirm new password</span>
              <input
                autoComplete="new-password"
                maxLength={72}
                minLength={8}
                required
                type="password"
                value={passwordForm.confirm_password}
                onChange={(event) => setPasswordForm({ ...passwordForm, confirm_password: event.target.value })}
              />
            </label>
          </div>
          <div className="profile-actions">
            <button className="btn-primary profile-submit" type="submit" disabled={passwordBusy}>
              {passwordBusy ? "Updating..." : "Update password"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
