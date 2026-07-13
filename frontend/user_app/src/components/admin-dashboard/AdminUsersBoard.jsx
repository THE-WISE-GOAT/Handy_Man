import React, { useEffect, useState, useMemo } from "react";
import { apiClient, normalizeApiError } from "@shared/api/client";
import "./AdminUsersBoard.css";

export default function AdminUsersBoard({ viewSlug }) {
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    const loadUsers = async () => {
      setIsLoading(true);
      setError("");
      try {
        const data = await apiClient.get("/users/");
        if (active) setUsers(Array.isArray(data) ? data : []);
      } catch (err) {
        if (!active) return;
        const normalized = normalizeApiError(err, "Failed to load users.");
        setError(normalized.message);
      } finally {
        if (active) setIsLoading(false);
      }
    };

    loadUsers();
    return () => {
      active = false;
    };
  }, []);

  const roleNames = (user) =>
    Array.isArray(user.roles) ? user.roles.map((r) => r.name) : [];

  const { workers, customers, admins } = useMemo(() => {
    const classify = (user) => {
      const names = roleNames(user).map((n) => String(n).toLowerCase());
      if (names.includes("admin")) return "admins";
      if (names.includes("worker")) return "workers";
      return "customers";
    };

    const buckets = { workers: [], customers: [], admins: [] };
    users.forEach((user) => {
      buckets[classify(user)].push(user);
    });
    return buckets;
  }, [users]);

  const renderTable = (title, list, accent) => (
    <section className="admin-section">
      <div className="admin-section__head">
        <h2>{title}</h2>
        <span className="admin-section__count">{list.length}</span>
      </div>
      {list.length === 0 ? (
        <p className="admin-section__empty">No records found.</p>
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Username</th>
                <th>Email</th>
                <th>Name</th>
                <th>Roles</th>
              </tr>
            </thead>
            <tbody>
              {list.map((user) => (
                <tr key={user.id} className={`admin-row admin-row--${accent}`}>
                  <td>{user.id}</td>
                  <td>{user.username}</td>
                  <td className="admin-cell-email">{user.email}</td>
                  <td>
                    {[user.firstName, user.lastName]
                      .filter(Boolean)
                      .join(" ") || "—"}
                  </td>
                  <td>
                    {roleNames(user).map((name) => (
                      <span key={name} className="admin-pill">
                        {name}
                      </span>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );

  return (
    <div className="admin-board">
      <div className="admin-board__head">
        <span className="card-flag">PLATFORM USER REGISTRY</span>
        <h1>ADMIN CONTROL DASHBOARD</h1>
        <p className="admin-board__sub">
          Live view of every customer, worker, and administrator in the system.
        </p>
      </div>

      {isLoading && <p className="admin-status">Loading users…</p>}
      {error && <p className="admin-status admin-status--error">{error}</p>}

      {!isLoading && !error && (
        <div className="admin-board__grid">
          {renderTable("Workers", workers, "worker")}
          {renderTable("Customers", customers, "customer")}
          {renderTable("Administrators", admins, "admin")}
        </div>
      )}
    </div>
  );
}
