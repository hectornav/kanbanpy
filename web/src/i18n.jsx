// i18n.js - lightweight, dependency-free translations (es / ca / en).
import { createContext, useContext, useState } from "react";

export const LANGS = [
  { id: "es", name: "Español", flag: "🇪🇸" },
  { id: "ca", name: "Català", flag: "🏴" },
  { id: "en", name: "English", flag: "🇬🇧" }
];

const T = {
  es: {
    "brand": "Kanbanpy Pro",
    "common.save": "Guardar", "common.cancel": "Cancelar", "common.create": "Crear",
    "common.delete": "Eliminar", "common.archive": "Archivar", "common.restore": "Restaurar",
    "common.clear": "Limpiar", "common.add": "Añadir", "common.send": "Enviar",
    "common.loading": "Cargando…", "common.logout": "Salir",
    "nav.board": "Tablero", "nav.list": "Lista", "nav.calendar": "Calendario", "nav.archive": "Archivo",
    "nav.newTask": "+ Nueva tarea", "nav.newBoard": "+ Tablero", "nav.boardSettings": "Ajustes del tablero",
    "nav.activity": "Actividad", "nav.theme": "Tema", "nav.background": "Fondo del tablero", "nav.language": "Idioma",
    "auth.welcome": "Bienvenido/a", "auth.loginSubtitle": "Inicia sesión para continuar",
    "auth.user": "Usuario", "auth.userPh": "Nombre de usuario", "auth.password": "Contraseña", "auth.passwordPh": "Contraseña",
    "auth.forgot": "¿Olvidaste tu contraseña?", "auth.noAccount": "¿No tienes cuenta?", "auth.register": "Regístrate",
    "auth.login": "Iniciar sesión", "auth.passMismatch": "Las contraseñas no coinciden.",
    "auth.createAccount": "Crear cuenta", "auth.registerSubtitle": "Gratis · Sin límites · Sin correo",
    "auth.chooseName": "Elige un nombre", "auth.min4": "Mínimo 4 caracteres", "auth.confirmPass": "Confirmar contraseña",
    "auth.repeatPass": "Repite tu contraseña", "auth.securityQ": "Pregunta de seguridad",
    "auth.securityQPh": "¿Nombre de tu primera mascota?", "auth.securityA": "Respuesta (para recuperar cuenta)",
    "auth.securityAPh": "No distingue mayúsculas", "auth.haveAccount": "¿Ya tienes cuenta?",
    "auth.recoverPass": "Recuperar contraseña", "auth.recoverSubtitle": "Responde tu pregunta de seguridad",
    "auth.yourUsername": "Tu nombre de usuario", "auth.question": "Pregunta:",
    "auth.notFound": "(usuario no encontrado o sin pregunta registrada)", "auth.answer": "Respuesta",
    "auth.yourAnswer": "Tu respuesta", "auth.newPassword": "Nueva contraseña", "auth.resetPass": "Restablecer contraseña",
    "auth.resetOk": "Contraseña restablecida. Ya puedes iniciar sesión.", "auth.backToLogin": "← Volver al inicio de sesión",
    "auth.tagline": "Tu forma de trabajar, organizada.",
    "feat.1": "Tablero Kanban multiusuario", "feat.2": "Prioridades, etiquetas y fechas",
    "feat.3": "Comparte tareas con otros usuarios", "feat.4": "Sincronización en vivo en cada pantalla",
    "col.ToDo": "Por hacer", "col.Doing": "En curso", "col.Done": "Hecho",
    "board.addInline": "+ Añadir", "board.closeBanner": "toca para cerrar",
    "board.searchPh": "🔍 Buscar tareas…", "board.prioAll": "Prioridad: todas",
    "prio.High": "Alta", "prio.Medium": "Media", "prio.Low": "Baja",
    "board.assigneeAll": "Asignado: todos", "board.me": "(yo)", "board.noMatch": "Sin tareas que coincidan con el filtro.",
    "board.bgCustom": "Color personalizado", "board.emptyArchive": "Aún no hay tareas archivadas. Marca una tarea como ✓ para archivarla.",
    "board.archivedOn": "archivada", "cal.noDate": "Sin fecha", "cal.today": "Hoy",
    "theme.nocturne": "Nocturne", "theme.nocturneSub": "Pizarra fría",
    "theme.frost": "Frost", "theme.frostSub": "Claro y nítido",
    "theme.meridian": "Meridian", "theme.meridianSub": "Grafito cálido",
    "task.newTask": "Nueva tarea", "task.detail": "Detalle de tarea", "task.title": "Título",
    "task.titlePh": "¿Qué hay que hacer?", "task.description": "Descripción", "task.descPh": "Detalles opcionales…",
    "task.priority": "Prioridad", "task.column": "Columna", "task.assignTo": "Asignar a", "task.unassigned": "Sin asignar",
    "task.dueDate": "Fecha límite", "task.tags": "Etiquetas", "task.tagsPh": "casa, urgente",
    "task.recurrence": "Repetición", "rec.none": "Sin repetición", "rec.daily": "Diaria", "rec.weekly": "Semanal", "rec.monthly": "Mensual",
    "task.subtasks": "Subtareas", "task.addSubtaskPh": "Añadir subtarea…",
    "task.comments": "Comentarios", "task.firstComment": "Sé el primero en comentar.", "task.commentPh": "Escribe un comentario…",
    "task.activity": "Actividad",
    "bs.newBoard": "Nuevo tablero", "bs.settings": "Ajustes del tablero", "bs.name": "Nombre",
    "bs.namePh": "Casa, Trabajo, Viaje…", "bs.color": "Color", "bs.shareAll": "Compartir con todos los usuarios",
    "bs.shareSpecific": "Compartir con usuarios concretos", "bs.deleteBoard": "Eliminar tablero",
    "bs.confirmDelete": "¿Eliminar el tablero \"{name}\" y todas sus tareas?",
    "act.title": "Actividad", "act.empty": "Sin actividad todavía.",
    "act.created": "creó", "act.edited": "editó", "act.moved": "movió a", "act.archived": "archivó",
    "act.restored": "restauró", "act.deleted": "eliminó"
  },
  ca: {
    "brand": "Kanbanpy Pro",
    "common.save": "Desa", "common.cancel": "Cancel·la", "common.create": "Crea",
    "common.delete": "Elimina", "common.archive": "Arxiva", "common.restore": "Restaura",
    "common.clear": "Neteja", "common.add": "Afegeix", "common.send": "Envia",
    "common.loading": "Carregant…", "common.logout": "Surt",
    "nav.board": "Tauler", "nav.list": "Llista", "nav.calendar": "Calendari", "nav.archive": "Arxiu",
    "nav.newTask": "+ Nova tasca", "nav.newBoard": "+ Tauler", "nav.boardSettings": "Configuració del tauler",
    "nav.activity": "Activitat", "nav.theme": "Tema", "nav.background": "Fons del tauler", "nav.language": "Idioma",
    "auth.welcome": "Benvingut/da", "auth.loginSubtitle": "Inicia la sessió per continuar",
    "auth.user": "Usuari", "auth.userPh": "Nom d'usuari", "auth.password": "Contrasenya", "auth.passwordPh": "Contrasenya",
    "auth.forgot": "Has oblidat la contrasenya?", "auth.noAccount": "No tens compte?", "auth.register": "Registra't",
    "auth.login": "Inicia la sessió", "auth.passMismatch": "Les contrasenyes no coincideixen.",
    "auth.createAccount": "Crea un compte", "auth.registerSubtitle": "Gratis · Sense límits · Sense correu",
    "auth.chooseName": "Tria un nom", "auth.min4": "Mínim 4 caràcters", "auth.confirmPass": "Confirma la contrasenya",
    "auth.repeatPass": "Repeteix la contrasenya", "auth.securityQ": "Pregunta de seguretat",
    "auth.securityQPh": "Nom de la teva primera mascota?", "auth.securityA": "Resposta (per recuperar el compte)",
    "auth.securityAPh": "No distingeix majúscules", "auth.haveAccount": "Ja tens compte?",
    "auth.recoverPass": "Recupera la contrasenya", "auth.recoverSubtitle": "Respon la teva pregunta de seguretat",
    "auth.yourUsername": "El teu nom d'usuari", "auth.question": "Pregunta:",
    "auth.notFound": "(usuari no trobat o sense pregunta registrada)", "auth.answer": "Resposta",
    "auth.yourAnswer": "La teva resposta", "auth.newPassword": "Nova contrasenya", "auth.resetPass": "Restableix la contrasenya",
    "auth.resetOk": "Contrasenya restablerta. Ja pots iniciar la sessió.", "auth.backToLogin": "← Torna a l'inici de sessió",
    "auth.tagline": "La teva manera de treballar, organitzada.",
    "feat.1": "Tauler Kanban multiusuari", "feat.2": "Prioritats, etiquetes i dates",
    "feat.3": "Comparteix tasques amb altres usuaris", "feat.4": "Sincronització en viu a cada pantalla",
    "col.ToDo": "Per fer", "col.Doing": "En curs", "col.Done": "Fet",
    "board.addInline": "+ Afegeix", "board.closeBanner": "toca per tancar",
    "board.searchPh": "🔍 Cerca tasques…", "board.prioAll": "Prioritat: totes",
    "prio.High": "Alta", "prio.Medium": "Mitjana", "prio.Low": "Baixa",
    "board.assigneeAll": "Assignat: tots", "board.me": "(jo)", "board.noMatch": "Cap tasca coincideix amb el filtre.",
    "board.bgCustom": "Color personalitzat", "board.emptyArchive": "Encara no hi ha tasques arxivades. Marca una tasca com a ✓ per arxivar-la.",
    "board.archivedOn": "arxivada", "cal.noDate": "Sense data", "cal.today": "Avui",
    "theme.nocturne": "Nocturne", "theme.nocturneSub": "Pissarra freda",
    "theme.frost": "Frost", "theme.frostSub": "Clar i nítid",
    "theme.meridian": "Meridian", "theme.meridianSub": "Grafit càlid",
    "task.newTask": "Nova tasca", "task.detail": "Detall de la tasca", "task.title": "Títol",
    "task.titlePh": "Què cal fer?", "task.description": "Descripció", "task.descPh": "Detalls opcionals…",
    "task.priority": "Prioritat", "task.column": "Columna", "task.assignTo": "Assigna a", "task.unassigned": "Sense assignar",
    "task.dueDate": "Data límit", "task.tags": "Etiquetes", "task.tagsPh": "casa, urgent",
    "task.recurrence": "Repetició", "rec.none": "Sense repetició", "rec.daily": "Diària", "rec.weekly": "Setmanal", "rec.monthly": "Mensual",
    "task.subtasks": "Subtasques", "task.addSubtaskPh": "Afegeix subtasca…",
    "task.comments": "Comentaris", "task.firstComment": "Sigues el primer a comentar.", "task.commentPh": "Escriu un comentari…",
    "task.activity": "Activitat",
    "bs.newBoard": "Nou tauler", "bs.settings": "Configuració del tauler", "bs.name": "Nom",
    "bs.namePh": "Casa, Feina, Viatge…", "bs.color": "Color", "bs.shareAll": "Comparteix amb tots els usuaris",
    "bs.shareSpecific": "Comparteix amb usuaris concrets", "bs.deleteBoard": "Elimina el tauler",
    "bs.confirmDelete": "Vols eliminar el tauler \"{name}\" i totes les seves tasques?",
    "act.title": "Activitat", "act.empty": "Encara no hi ha activitat.",
    "act.created": "va crear", "act.edited": "va editar", "act.moved": "va moure a", "act.archived": "va arxivar",
    "act.restored": "va restaurar", "act.deleted": "va eliminar"
  },
  en: {
    "brand": "Kanbanpy Pro",
    "common.save": "Save", "common.cancel": "Cancel", "common.create": "Create",
    "common.delete": "Delete", "common.archive": "Archive", "common.restore": "Restore",
    "common.clear": "Clear", "common.add": "Add", "common.send": "Send",
    "common.loading": "Loading…", "common.logout": "Log out",
    "nav.board": "Board", "nav.list": "List", "nav.calendar": "Calendar", "nav.archive": "Archive",
    "nav.newTask": "+ New task", "nav.newBoard": "+ Board", "nav.boardSettings": "Board settings",
    "nav.activity": "Activity", "nav.theme": "Theme", "nav.background": "Board background", "nav.language": "Language",
    "auth.welcome": "Welcome", "auth.loginSubtitle": "Sign in to continue",
    "auth.user": "Username", "auth.userPh": "Username", "auth.password": "Password", "auth.passwordPh": "Password",
    "auth.forgot": "Forgot your password?", "auth.noAccount": "No account?", "auth.register": "Sign up",
    "auth.login": "Sign in", "auth.passMismatch": "Passwords don't match.",
    "auth.createAccount": "Create account", "auth.registerSubtitle": "Free · No limits · No email",
    "auth.chooseName": "Choose a name", "auth.min4": "At least 4 characters", "auth.confirmPass": "Confirm password",
    "auth.repeatPass": "Repeat your password", "auth.securityQ": "Security question",
    "auth.securityQPh": "Your first pet's name?", "auth.securityA": "Answer (to recover your account)",
    "auth.securityAPh": "Case-insensitive", "auth.haveAccount": "Already have an account?",
    "auth.recoverPass": "Recover password", "auth.recoverSubtitle": "Answer your security question",
    "auth.yourUsername": "Your username", "auth.question": "Question:",
    "auth.notFound": "(user not found or no question set)", "auth.answer": "Answer",
    "auth.yourAnswer": "Your answer", "auth.newPassword": "New password", "auth.resetPass": "Reset password",
    "auth.resetOk": "Password reset. You can sign in now.", "auth.backToLogin": "← Back to sign in",
    "auth.tagline": "Your way of working, organized.",
    "feat.1": "Multi-user Kanban board", "feat.2": "Priorities, tags and dates",
    "feat.3": "Share tasks with other users", "feat.4": "Live sync on every screen",
    "col.ToDo": "To do", "col.Doing": "In progress", "col.Done": "Done",
    "board.addInline": "+ Add", "board.closeBanner": "tap to close",
    "board.searchPh": "🔍 Search tasks…", "board.prioAll": "Priority: all",
    "prio.High": "High", "prio.Medium": "Medium", "prio.Low": "Low",
    "board.assigneeAll": "Assignee: all", "board.me": "(me)", "board.noMatch": "No tasks match the filter.",
    "board.bgCustom": "Custom color", "board.emptyArchive": "No archived tasks yet. Mark a task as ✓ to archive it.",
    "board.archivedOn": "archived", "cal.noDate": "No date", "cal.today": "Today",
    "theme.nocturne": "Nocturne", "theme.nocturneSub": "Cool slate",
    "theme.frost": "Frost", "theme.frostSub": "Crisp & light",
    "theme.meridian": "Meridian", "theme.meridianSub": "Warm graphite",
    "task.newTask": "New task", "task.detail": "Task detail", "task.title": "Title",
    "task.titlePh": "What needs doing?", "task.description": "Description", "task.descPh": "Optional details…",
    "task.priority": "Priority", "task.column": "Column", "task.assignTo": "Assign to", "task.unassigned": "Unassigned",
    "task.dueDate": "Due date", "task.tags": "Tags", "task.tagsPh": "home, urgent",
    "task.recurrence": "Repeat", "rec.none": "No repeat", "rec.daily": "Daily", "rec.weekly": "Weekly", "rec.monthly": "Monthly",
    "task.subtasks": "Subtasks", "task.addSubtaskPh": "Add subtask…",
    "task.comments": "Comments", "task.firstComment": "Be the first to comment.", "task.commentPh": "Write a comment…",
    "task.activity": "Activity",
    "bs.newBoard": "New board", "bs.settings": "Board settings", "bs.name": "Name",
    "bs.namePh": "Home, Work, Trip…", "bs.color": "Color", "bs.shareAll": "Share with all users",
    "bs.shareSpecific": "Share with specific users", "bs.deleteBoard": "Delete board",
    "bs.confirmDelete": "Delete board \"{name}\" and all its tasks?",
    "act.title": "Activity", "act.empty": "No activity yet.",
    "act.created": "created", "act.edited": "edited", "act.moved": "moved to", "act.archived": "archived",
    "act.restored": "restored", "act.deleted": "deleted"
  }
};

const LangContext = createContext(null);

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(() => {
    const saved = localStorage.getItem("kanban.lang");
    if (saved && T[saved]) return saved;
    const nav = (navigator.language || "es").slice(0, 2);
    return T[nav] ? nav : "es";
  });
  function setLang(l) {
    setLangState(l);
    localStorage.setItem("kanban.lang", l);
    document.documentElement.lang = l;
  }
  function t(key, params) {
    let s = (T[lang] && T[lang][key]) ?? T.es[key] ?? key;
    if (params) for (const k in params) s = s.replace(`{${k}}`, params[k]);
    return s;
  }
  return <LangContext.Provider value={{ lang, setLang, t }}>{children}</LangContext.Provider>;
}

export function useT() {
  return useContext(LangContext);
}
