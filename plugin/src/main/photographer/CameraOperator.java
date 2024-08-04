package edu.whimc.photographer;

import com.corundumstudio.socketio.SocketIOClient;
import com.gmail.filoghost.holographicdisplays.api.HologramsAPI;
import edu.whimc.observations.models.Observation;
import java.net.SocketAddress;
import java.util.Collection;
import java.util.HashSet;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import javax.annotation.Nullable;
import org.bukkit.Bukkit;
import org.bukkit.ChatColor;
import org.bukkit.GameMode;
import org.bukkit.Location;
import org.bukkit.entity.Player;

public class CameraOperator {

    private static final Set<CameraOperator> operators = new HashSet<>();

    private final Photographer plugin;
    private final UUID playerUuid;
    private final UUID clientUuid;
    private final SocketAddress clientAddress;

    /**
     * Previous things about the player
     */
    private GameMode prevGameMode;
    private Location prevLocation;

    private @Nullable Observation currentObservation = null;

    private CameraOperator(Photographer plugin, Player player, SocketIOClient client) {
        this.plugin = plugin;
        this.playerUuid = player.getUniqueId();
        this.clientUuid = client.get("uuid");
        clientAddress = client.getRemoteAddress();
    }

    public static Optional<CameraOperator> registerCameraOperator(Photographer plugin, Player player,
                                                                  SocketIOClient client) {
        if (getCameraOperator(player.getUniqueId()).isPresent()
                || getCameraOperator(client.get("uuid")).isPresent()) {
            return Optional.empty();
        }

        CameraOperator operator = new CameraOperator(plugin, player, client);

        // Save player state
        operator.prevLocation = player.getLocation();
        operator.prevGameMode = player.getGameMode();

        // Prepare the player for being a camera operator
        player.setGameMode(GameMode.SPECTATOR);

        // Hide all players
        Bukkit.getOnlinePlayers().forEach(p -> player.hidePlayer(plugin, p));

        // Hide all holograms from the player
        HologramsAPI.getHolograms(plugin.getObservationsPlugin()).forEach(hologram ->
                hologram.getVisibilityManager().hideTo(player));

        CameraOperator.operators.add(operator);

        client.sendEvent("cameraman_connect", player.getName());

        return Optional.of(operator);
    }

    public void unregister() {
        Player player = getPlayer();
        Utils.msg(player, "&6&lYou are no longer a photographer");
        CameraOperator.operators.remove(this);

        this.plugin.getClient(this.clientUuid).ifPresent(co ->
                co.sendEvent("cameraman_disconnect", player.getName())
        );

        // Restore the state of the player
        player.teleport(this.prevLocation);
        player.setGameMode(this.prevGameMode);

        // Show all players
        Bukkit.getOnlinePlayers().forEach(p -> player.showPlayer(this.plugin, p));

        // Show all holograms
        HologramsAPI.getHolograms(plugin.getObservationsPlugin()).forEach(hologram ->
                hologram.getVisibilityManager().resetVisibility(player));
    }

    public static Optional<CameraOperator> getAvailableOperator() {
        return CameraOperator.operators.stream()
                .filter(CameraOperator::isAvailable)
                .findFirst();
    }

    public static Collection<CameraOperator> getAllCameraOperators() {
        return CameraOperator.operators;
    }

    public static Optional<CameraOperator> getCameraOperator(UUID playerOrSocketUuid) {
        for (CameraOperator operator : CameraOperator.operators) {
            if (operator.playerUuid.equals(playerOrSocketUuid)
                    || operator.clientUuid.equals(playerOrSocketUuid)) {
                return Optional.of(operator);
            }
        }
        return Optional.empty();
    }

    public void photograph(Observation observation) {
        this.currentObservation = observation;
        Player player = getPlayer();
        Utils.msg(player, "&ePhotographing observation &6&lID " + observation.getId() +
                "&e from &6&l" + observation.getPlayer());

        // Make the observation invisible if the hologram exists
        if (observation.getHologram() != null) {
            observation.getHologram().getVisibilityManager().hideTo(player);
        }
        boolean changedWorlds = player.getWorld().equals(observation.getViewLocation().getWorld());
        player.teleport(observation.getViewLocation());

        String strippedObservation = ChatColor.stripColor(observation.getObservation());

        Bukkit.getScheduler().runTaskAsynchronously(this.plugin, () ->
                        getClient().sendEvent("screenshot", observation.getId(), observation.getPlayer(), strippedObservation, changedWorlds)
                );
    }

    public Player getPlayer() {
        return Bukkit.getPlayer(this.playerUuid);
    }

    public boolean isAvailable() {
        return this.currentObservation == null;
    }

    public UUID getPlayerUuid() {
        return this.playerUuid;
    }

    public UUID getClientUuid() {
        return this.clientUuid;
    }

    public SocketAddress getClientAddress() {
        return this.clientAddress;
    }

    public @Nullable Observation getCurrentObservation() {
        return this.currentObservation;
    }

    public void setCurrentObservation(@Nullable Observation observation) {
        this.currentObservation = observation;
    }

    public SocketIOClient getClient() {
        // This should never be null
        return this.plugin.getClient(this.clientUuid).get();
    }

}
